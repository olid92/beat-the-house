import pandas as pd
from datetime import datetime

dictionary = pd.read_csv("dictionary.csv", header=0)
season_19_20 = pd.read_csv("season-1920.csv")
season_20_21 = pd.read_csv("season-2021.csv")
season_21_22 = pd.read_csv("season-2122.csv")
season_22_23 = pd.read_csv("season-2223.csv")
season_23_24 = pd.read_csv("season-2324.csv")
season_24_25 = pd.read_csv("season-2425.csv")
season_25_26 = pd.read_csv("season-2526.csv")

all = pd.concat(
    [season_19_20,
     season_20_21,
     season_21_22,
     season_22_23,
     season_23_24,
     season_24_25,
     season_25_26]
     )

all_seasons = all.rename(columns={
    "Date": "match_date",
    "HomeTeam": "home_team",
    "AwayTeam": "away_team",
    "FTHG": "full_time_home_team_goals",
    "FTAG": "full_time_away_team_goals",
    "FTR": "full_time_result",
    "HTHG": "half_time_home_team_goals",
    "HTAG": "half_time_away_team_goals",
    "HTR": "half_time_result",
    "Referee": "match_referee",
    "HS": "home_team_shots",
    "AS": "away_team_shots",
    "HST": "home_team_shots_on_target",
    "AST": "away_team_shots_on_target",
    "HF": "home_team_fouls_committed",
    "AF": "away_team_fouls_committed",
    "HC": "home_team_corners",
    "AC": "away_team_corners",
    "HY": "home_team_yellow_cards",
    "AY": "away_team_yellow_cards",
    "HR": "home_team_red_cards",
    "AR": "away_team_red_cards"
    })

df = all_seasons

# Ensure date column is datetime (dayfirst=True since CSVs commonly use DD/MM/YYYY)
df['match_date'] = pd.to_datetime(df['match_date'], format='%Y-%m-%d')


def get_season(match_date):
    """
    Determine the season based on match date.
    Premier League seasons run August to May.
    E.g., a match on 2019-09-01 is in season 2019/20
    """
    year = match_date.year
    month = match_date.month

    if month >= 8:
        season = f"{year}/{year + 1 - 2000:02d}"
    else:
        season = f"{year - 1}/{year - 2000:02d}"

    return season


# Add season column
df['season'] = df['match_date'].apply(get_season)

# Sort so the earliest match in each season is the start of gameweek 1
df = df.sort_values(['season', 'match_date']).reset_index(drop=True)

def add_gameweeks(df):
    """
    Assign gameweeks across all seasons in one pass.
    Each team plays exactly one match per gameweek, so we rank each team's
    matches chronologically *within their season* (1..38).
    For each fixture, gameweek = max of the two teams' match numbers —
    this handles postponed/rescheduled games correctly.
    """
    # Build long-format: one row per (team, match)
    home = df[['season', 'match_date']].assign(team=df['home_team'],
                                               match_idx=df.index)
    away = df[['season', 'match_date']].assign(team=df['away_team'],
                                               match_idx=df.index)
    long = pd.concat([home, away], ignore_index=True)

    # Rank each team's matches chronologically *within each season*
    long = long.sort_values(['season', 'team', 'match_date'])
    long['team_match_no'] = long.groupby(['season', 'team']).cumcount() + 1

    # For each fixture, gameweek = max of the two teams' match numbers
    gw = long.groupby('match_idx')['team_match_no'].max()

    df = df.copy()
    df['gameweek'] = df.index.map(gw)
    df['gameweek'] = df['gameweek'].clip(lower=1, upper=38)
    return df

df = add_gameweeks(df)

# Display sample of enriched data
print(df.head(20))
print(f"\nDataset shape: {df.shape}")
print(f"Seasons in dataset: {sorted(df['season'].unique())}")

# Sanity check: per-season gameweek range
print("\nGameweek range per season:")
print(df.groupby('season')['gameweek'].agg(['min', 'max', 'nunique']))

# Save enriched dataset
df.to_csv('seasons-1920_to_2526.csv', index=False)
print("\nEnriched data saved to 'seasons-1920_to_2526.csv'")