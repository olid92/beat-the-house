import pandas as pd

# ======================
# Config
# ======================
INPUT_FILE = "seasons-1920_to_2526.csv"
OUTPUT_FILE = "gameweekranking.csv"


# ======================
# Load data
# ======================
df = pd.read_csv(INPUT_FILE)

required_cols = [
    "season",
    "gameweek",
    "home_team",
    "away_team",
    "full_time_home_team_goals",
    "full_time_away_team_goals",
    "full_time_result"
]

missing = [c for c in required_cols if c not in df.columns]
if missing:
    raise ValueError(f"Missing columns: {missing}")


# ======================
# Build long format
# ======================
def build_long_format(df):

    home = pd.DataFrame({
        "season": df["season"],
        "gameweek": df["gameweek"],
        "team": df["home_team"],
        "goals_for": df["full_time_home_team_goals"],
        "goals_against": df["full_time_away_team_goals"],
        "is_home": 1,
        "result_raw": df["full_time_result"]
    })

    away = pd.DataFrame({
        "season": df["season"],
        "gameweek": df["gameweek"],
        "team": df["away_team"],
        "goals_for": df["full_time_away_team_goals"],
        "goals_against": df["full_time_home_team_goals"],
        "is_home": 0,
        "result_raw": df["full_time_result"]
    })

    df_long = pd.concat([home, away], ignore_index=True)

    def get_points(row):
        if row["is_home"] == 1:
            if row["result_raw"] == "H":
                return 3
            elif row["result_raw"] == "D":
                return 1
            else:
                return 0
        else:
            if row["result_raw"] == "A":
                return 3
            elif row["result_raw"] == "D":
                return 1
            else:
                return 0

    def result_label(row):
        if row["points"] == 3:
            return "W"
        elif row["points"] == 1:
            return "D"
        else:
            return "L"

    df_long["points"] = df_long.apply(get_points, axis=1)
    df_long["result"] = df_long.apply(result_label, axis=1)

    return df_long


long_df = build_long_format(df)


# ======================
# Precompute form streaks
# ======================
def compute_form_metrics(df_long):

    df_long = df_long.sort_values(["season", "team", "gameweek"])

    # initialise counters
    df_long["games_since_win"] = 0
    df_long["games_since_draw"] = 0
    df_long["games_since_loss"] = 0

    for (season, team), group in df_long.groupby(["season", "team"]):
        g = group.sort_values("gameweek").copy()

        win_streak = 0
        draw_streak = 0
        loss_streak = 0

        for i, row in g.iterrows():

            g.loc[i, "games_since_win"] = win_streak
            g.loc[i, "games_since_draw"] = draw_streak
            g.loc[i, "games_since_loss"] = loss_streak

            if row["result"] == "W":
                win_streak = 0
                draw_streak += 1
                loss_streak += 1
            elif row["result"] == "D":
                draw_streak = 0
                win_streak += 1
                loss_streak += 1
            else:
                loss_streak = 0
                win_streak += 1
                draw_streak += 1

        df_long.loc[g.index, [
            "games_since_win",
            "games_since_draw",
            "games_since_loss"
        ]] = g[[
            "games_since_win",
            "games_since_draw",
            "games_since_loss"
        ]]

    return df_long


long_df = compute_form_metrics(long_df)


# ======================
# Rankings calculation
# ======================
all_rankings = []

for season in sorted(long_df["season"].unique()):

    season_df = long_df[long_df["season"] == season]
    teams = sorted(season_df["team"].unique())
    max_gw = season_df["gameweek"].max()

    prev_positions = {}

    for gw in range(1, max_gw + 1):

        played = season_df[season_df["gameweek"] <= gw]

        table = (
            played.groupby("team")
            .agg(
                matches_played=("points", "count"),
                points=("points", "sum"),
                goals_for=("goals_for", "sum"),
                goals_against=("goals_against", "sum")
            )
            .reset_index()
        )

        table["goal_difference"] = (
            table["goals_for"] - table["goals_against"]
        )

        # Ensure all teams exist
        for t in teams:
            if t not in table["team"].values:
                table = pd.concat([
                    table,
                    pd.DataFrame([{
                        "team": t,
                        "matches_played": 0,
                        "points": 0,
                        "goals_for": 0,
                        "goals_against": 0,
                        "goal_difference": 0
                    }])
                ], ignore_index=True)

        # Sort (ranking rules)
        table = table.sort_values(
            by=["points", "goal_difference", "goals_for"],
            ascending=False
        ).reset_index(drop=True)

        table["position"] = table.index + 1

        # ======================
        # Position change
        # ======================
        position_change = []

        for _, row in table.iterrows():
            team = row["team"]
            current_pos = row["position"]

            prev_pos = prev_positions.get(team)

            if prev_pos is None:
                position_change.append(None)
            else:
                position_change.append(prev_pos - current_pos)

        table["position_change"] = position_change

        # Update tracker
        prev_positions = dict(zip(table["team"], table["position"]))

        # ======================
        # Merge form metrics for THIS GW
        # ======================
        gw_form = season_df[season_df["gameweek"] == gw][[
            "team",
            "games_since_win",
            "games_since_draw",
            "games_since_loss"
        ]]

        table = table.merge(gw_form, on="team", how="left")

        # Add metadata
        table["season"] = season
        table["gameweek"] = gw

        # Column order
        table = table[[
            "season",
            "gameweek",
            "position",
            "position_change",
            "team",
            "matches_played",
            "points",
            "goal_difference",
            "goals_for",
            "goals_against",
            "games_since_win",
            "games_since_draw",
            "games_since_loss"
        ]]

        all_rankings.append(table)


# ======================
# Save
# ======================
ranking_df = pd.concat(all_rankings, ignore_index=True)

ranking_df.to_csv(OUTPUT_FILE, index=False)

print(f"✅ Saved to {OUTPUT_FILE}")
print(ranking_df.head())