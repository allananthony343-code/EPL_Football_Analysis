"""
logic.py — Helper Functions for Premier League Analytics
=========================================================
This file contains all the functions used by main.py.
Each function does one specific job (loading data, ranking
players, building tables etc.) to keep the code clean and easy
to understand.
"""

# ─── IMPORTS ─────────────────────────────────────────────────────────────────
import pandas as pd      # for working with tabular data
import sqlite3           # for reading from the database


# ─── 1. LOAD DATA ─────────────────────────────────────────────────────────────
def load_data():
    """
    Loads the CSV file and connects to the SQLite database.

    Returns:
        df   — a pandas DataFrame with all player stats from the CSV
        conn — a live SQLite connection to football_data.db
    """

    # Read the CSV file into a DataFrame
    df = pd.read_csv("data.csv", encoding="utf-8", encoding_errors="ignore")

    # Remove any accidental spaces from column names
    df.columns = df.columns.str.strip()

    # Connect to the SQLite database
    conn = sqlite3.connect("football_data.db")

    return df, conn


# ─── 2. FIND PLAYER (fuzzy / partial name search) ────────────────────────────
def find_player(df, search_term):
    """
    Searches for players whose name contains the search_term.
    The search is case-insensitive so 'salah' will find 'Mohamed Salah'.

    Parameters:
        df          — the full player DataFrame
        search_term — the partial or full name typed by the user

    Returns:
        A DataFrame of matching players (could be 1 or many rows).
    """

    # Convert both the column and the search term to lowercase before comparing
    # This way 'saka' matches 'Bukayo Saka', 'SAKA', etc.
    mask = df["player_name"].str.lower().str.contains(search_term.lower(), na=False)

    # Return only the rows where the name matched
    matches = df[mask].reset_index(drop=True)

    return matches


# ─── 3. BEST STRIKER ─────────────────────────────────────────────────────────
def best_striker(df):
    """
    Ranks forwards (position == 'F') using a composite score made up of:
      - Goals (most important)
      - Expected goals (xG) — shows clinical finishing
      - Shots on target — shows attacking threat
      - Big chances missed (penalty — fewer is better)
      - Rating

    Returns the top 10 strikers as a DataFrame.
    """

    # Filter to only forwards
    forwards = df[df["position"] == "F"].copy()

    # Only keep players with a meaningful sample size (at least 5 appearances)
    forwards = forwards[forwards["appearances"] >= 5]

    # ── Build the composite score ──
    # We normalise each column to a 0–1 scale so they can be added fairly.
    # A higher score is always better.

    def normalise(series):
        """Scales a series so its values fall between 0 and 1."""
        min_val = series.min()
        max_val = series.max()
        if max_val == min_val:
            return series * 0          # avoid division by zero
        return (series - min_val) / (max_val - min_val)

    # Normalise each factor
    forwards["norm_goals"]      = normalise(forwards["goals"])
    forwards["norm_xg"]         = normalise(forwards["expectedGoals"])
    forwards["norm_sot"]        = normalise(forwards["shotsOnTarget"])
    forwards["norm_rating"]     = normalise(forwards["rating"])

    # Big chances missed — lower is better, so we invert it
    forwards["norm_bcm"]        = 1 - normalise(forwards["bigChancesMissed"])

    # Weighted sum — goals count the most
    forwards["striker_score"] = (
        forwards["norm_goals"]  * 0.40 +
        forwards["norm_xg"]     * 0.20 +
        forwards["norm_sot"]    * 0.15 +
        forwards["norm_bcm"]    * 0.15 +
        forwards["norm_rating"] * 0.10
    )

    # Round the score to 3 decimal places for display
    forwards["striker_score"] = forwards["striker_score"].round(3)

    # Select the columns we want to show
    output_cols = ["player_name", "team_name", "goals", "expectedGoals",
                   "shotsOnTarget", "bigChancesMissed", "rating", "striker_score"]

    # Sort by score descending and return the top 10
    top10 = forwards.sort_values("striker_score", ascending=False)[output_cols].head(10)

    # Rename columns to be more readable
    top10.columns = ["Player", "Club", "Goals", "xG", "Shots on Target",
                     "Big Chances Missed", "Rating", "Score"]

    return top10.reset_index(drop=True)


# ─── 4. MOST CREATIVE PLAYER ─────────────────────────────────────────────────
def most_creative_player(df):
    """
    Ranks ALL outfield players by creativity using:
      - Key passes (passes that directly lead to a shot)
      - Assists
      - Big chances created
      - Expected assists (xA)
      - Accurate final third passes

    Returns top 10 most creative players.
    """

    # Include all outfield positions (forwards, midfielders, defenders)
    outfield = df[df["position"] != "G"].copy()

    # Only players with at least 5 appearances
    outfield = outfield[outfield["appearances"] >= 5]

    def normalise(series):
        min_val = series.min()
        max_val = series.max()
        if max_val == min_val:
            return series * 0
        return (series - min_val) / (max_val - min_val)

    # Normalise each creativity factor
    outfield["norm_keypasses"]    = normalise(outfield["keyPasses"])
    outfield["norm_assists"]      = normalise(outfield["assists"])
    outfield["norm_bigchances"]   = normalise(outfield["bigChancesCreated"])
    outfield["norm_xa"]           = normalise(outfield["expectedAssists"])
    outfield["norm_finalthird"]   = normalise(outfield["accurateFinalThirdPasses"])

    # Build the creativity score — key passes and big chances created matter most
    outfield["creativity_score"] = (
        outfield["norm_keypasses"]  * 0.30 +
        outfield["norm_assists"]    * 0.25 +
        outfield["norm_bigchances"] * 0.25 +
        outfield["norm_xa"]         * 0.10 +
        outfield["norm_finalthird"] * 0.10
    )

    outfield["creativity_score"] = outfield["creativity_score"].round(3)

    output_cols = ["player_name", "team_name", "position", "keyPasses",
                   "assists", "bigChancesCreated", "expectedAssists", "creativity_score"]

    top10 = outfield.sort_values("creativity_score", ascending=False)[output_cols].head(10)

    top10.columns = ["Player", "Club", "Pos", "Key Passes", "Assists",
                     "Big Chances Created", "xA", "Score"]

    return top10.reset_index(drop=True)


# ─── 5. BEST DEFENDER ────────────────────────────────────────────────────────
def best_defender(df):
    """
    Ranks defenders (position == 'D') using:
      - Tackles won
      - Interceptions
      - Clearances
      - Aerial duels won percentage
      - Errors leading to goals (inverted — fewer is better)
      - Rating

    Returns top 10 defenders.
    """

    # Filter to only defenders
    defenders = df[df["position"] == "D"].copy()

    # At least 5 appearances
    defenders = defenders[defenders["appearances"] >= 5]

    def normalise(series):
        min_val = series.min()
        max_val = series.max()
        if max_val == min_val:
            return series * 0
        return (series - min_val) / (max_val - min_val)

    # Normalise each defensive metric
    defenders["norm_tackles"]      = normalise(defenders["tacklesWon"])
    defenders["norm_interceptions"]= normalise(defenders["interceptions"])
    defenders["norm_clearances"]   = normalise(defenders["clearances"])
    defenders["norm_aerial"]       = normalise(defenders["aerialDuelsWonPercentage"])
    defenders["norm_rating"]       = normalise(defenders["rating"])

    # Errors leading to a goal — lower is better, so we invert
    defenders["norm_errors"]       = 1 - normalise(defenders["errorLeadToGoal"])

    # Build the defensive score
    defenders["defender_score"] = (
        defenders["norm_tackles"]       * 0.25 +
        defenders["norm_interceptions"] * 0.25 +
        defenders["norm_clearances"]    * 0.15 +
        defenders["norm_aerial"]        * 0.15 +
        defenders["norm_errors"]        * 0.10 +
        defenders["norm_rating"]        * 0.10
    )

    defenders["defender_score"] = defenders["defender_score"].round(3)

    output_cols = ["player_name", "team_name", "tacklesWon", "interceptions",
                   "clearances", "aerialDuelsWonPercentage", "errorLeadToGoal",
                   "rating", "defender_score"]

    top10 = defenders.sort_values("defender_score", ascending=False)[output_cols].head(10)

    top10.columns = ["Player", "Club", "Tackles Won", "Interceptions",
                     "Clearances", "Aerial %", "Errors→Goal", "Rating", "Score"]

    return top10.reset_index(drop=True)


# ─── 6. BEST GOALKEEPER ──────────────────────────────────────────────────────
def best_goalkeeper(df):
    """
    Ranks goalkeepers (position == 'G') using:
      - Saves
      - Clean sheets
      - Goals prevented
      - Save percentage (saved shots / total shots faced)
      - Errors leading to goal (inverted)
      - Rating

    Returns top 10 goalkeepers.
    """

    # Filter to only goalkeepers
    keepers = df[df["position"] == "G"].copy()

    # At least 5 appearances
    keepers = keepers[keepers["appearances"] >= 5]

    # Calculate save percentage manually
    # Total shots faced = saves + goals conceded (approximate)
    keepers["total_shots_faced"] = keepers["saves"] + keepers["goalsConceded"]

    # Avoid division by zero — if total shots faced is 0, save pct = 0
    keepers["save_pct"] = keepers.apply(
        lambda row: (row["saves"] / row["total_shots_faced"] * 100)
                    if row["total_shots_faced"] > 0 else 0,
        axis=1
    )

    def normalise(series):
        min_val = series.min()
        max_val = series.max()
        if max_val == min_val:
            return series * 0
        return (series - min_val) / (max_val - min_val)

    # Normalise each goalkeeping metric
    keepers["norm_saves"]     = normalise(keepers["saves"])
    keepers["norm_cs"]        = normalise(keepers["cleanSheet"])
    keepers["norm_prevented"] = normalise(keepers["goalsPrevented"])
    keepers["norm_save_pct"]  = normalise(keepers["save_pct"])
    keepers["norm_rating"]    = normalise(keepers["rating"])

    # Errors leading to goal — lower is better, so we invert
    keepers["norm_errors"]    = 1 - normalise(keepers["errorLeadToGoal"])

    # Build the goalkeeper score
    keepers["gk_score"] = (
        keepers["norm_saves"]     * 0.25 +
        keepers["norm_cs"]        * 0.20 +
        keepers["norm_prevented"] * 0.20 +
        keepers["norm_save_pct"]  * 0.15 +
        keepers["norm_errors"]    * 0.10 +
        keepers["norm_rating"]    * 0.10
    )

    keepers["gk_score"] = keepers["gk_score"].round(3)

    output_cols = ["player_name", "team_name", "saves", "cleanSheet",
                   "goalsPrevented", "save_pct", "errorLeadToGoal", "rating", "gk_score"]

    top10 = keepers.sort_values("gk_score", ascending=False)[output_cols].head(10)

    top10.columns = ["Player", "Club", "Saves", "Clean Sheets",
                     "Goals Prevented", "Save %", "Errors→Goal", "Rating", "Score"]

    # Round save percentage for display
    top10["Save %"] = top10["Save %"].round(1)

    return top10.reset_index(drop=True)


# ─── 7. TEAM TABLE ───────────────────────────────────────────────────────────
def team_table(df):
    """
    Builds a summary table for all 20 teams showing:
      - Total goals scored
      - Average player rating (team performance proxy)
      - Average touches per player (possession proxy)
      - Total assists
      - A simple performance score

    Returns a DataFrame sorted by performance score.
    """

    # Group all rows by team name and aggregate statistics
    team_stats = df.groupby("team_name").agg(
        Players        = ("player_name", "count"),         # number of players in dataset
        Total_Goals    = ("goals", "sum"),                  # all goals added up
        Total_Assists  = ("assists", "sum"),                 # all assists added up
        Avg_Rating     = ("rating", "mean"),                # average player rating
        Avg_Touches    = ("touches", "mean"),               # avg touches (possession proxy)
        Total_Saves    = ("saves", "sum"),                  # for defensive context
    ).reset_index()

    # Round averages to 2 decimal places
    team_stats["Avg_Rating"]  = team_stats["Avg_Rating"].round(2)
    team_stats["Avg_Touches"] = team_stats["Avg_Touches"].round(1)

    # ── Build a simple team performance score ──
    # We combine goals, assists and average rating — normalised

    def normalise(series):
        min_val = series.min()
        max_val = series.max()
        if max_val == min_val:
            return series * 0
        return (series - min_val) / (max_val - min_val)

    team_stats["norm_goals"]   = normalise(team_stats["Total_Goals"])
    team_stats["norm_assists"] = normalise(team_stats["Total_Assists"])
    team_stats["norm_rating"]  = normalise(team_stats["Avg_Rating"])
    team_stats["norm_touches"] = normalise(team_stats["Avg_Touches"])

    # Performance score: goals and rating matter most
    team_stats["Performance_Score"] = (
        team_stats["norm_goals"]   * 0.40 +
        team_stats["norm_assists"] * 0.25 +
        team_stats["norm_rating"]  * 0.25 +
        team_stats["norm_touches"] * 0.10
    )

    team_stats["Performance_Score"] = team_stats["Performance_Score"].round(3)

    # Drop the normalised helper columns — they were just for the calculation
    team_stats = team_stats.drop(columns=["norm_goals", "norm_assists",
                                          "norm_rating", "norm_touches"])

    # Sort by performance score (best team first)
    team_stats = team_stats.sort_values("Performance_Score", ascending=False)

    # Add a rank column starting at 1
    team_stats.insert(0, "Rank", range(1, len(team_stats) + 1))

    # Rename columns for display
    team_stats.columns = ["Rank", "Club", "Players", "Goals", "Assists",
                          "Avg Rating", "Avg Touches", "Total Saves", "Perf. Score"]

    return team_stats.reset_index(drop=True)


# ─── 8. SHOW PLAYER PROFILE ──────────────────────────────────────────────────
def show_player_profile(player_row, conn):
    """
    Displays a detailed profile for a single player.

    Parameters:
        player_row — a single row from the DataFrame (selected by the user)
        conn       — the SQLite database connection (to pull DB info)
    """

    name = player_row["player_name"]
    print(f"\n{'=' * 55}")
    print(f"  🧑 PLAYER PROFILE: {name.upper()}")
    print(f"{'=' * 55}")

    # ── Basic Info ──
    print(f"  Club        : {player_row['team_name']}")
    print(f"  Position    : {player_row['position']}")
    print(f"  Appearances : {player_row['appearances']}")
    print(f"  Minutes     : {player_row['minutesPlayed']}")
    print(f"  Rating      : {player_row['rating']:.2f}")

    # ── Attacking Stats (for forwards and midfielders) ──
    if player_row["position"] in ["F", "M"]:
        print(f"\n  ⚽ ATTACKING:")
        print(f"  Goals          : {player_row['goals']}")
        print(f"  Assists        : {player_row['assists']}")
        print(f"  xG             : {player_row['expectedGoals']:.2f}")
        print(f"  xA             : {player_row['expectedAssists']:.2f}")
        print(f"  Key Passes     : {player_row['keyPasses']}")
        print(f"  Big Chances Created: {player_row['bigChancesCreated']}")
        print(f"  Shots on Target: {player_row['shotsOnTarget']}")

    # ── Defensive Stats (for defenders and midfielders) ──
    if player_row["position"] in ["D", "M"]:
        print(f"\n  🛡️  DEFENSIVE:")
        print(f"  Tackles Won    : {player_row['tacklesWon']}")
        print(f"  Interceptions  : {player_row['interceptions']}")
        print(f"  Clearances     : {player_row['clearances']}")
        print(f"  Aerial Won %   : {player_row['aerialDuelsWonPercentage']:.1f}%")

    # ── Goalkeeper Stats ──
    if player_row["position"] == "G":
        print(f"\n  🧤 GOALKEEPING:")
        print(f"  Saves          : {player_row['saves']}")
        print(f"  Clean Sheets   : {player_row['cleanSheet']}")
        print(f"  Goals Prevented: {player_row['goalsPrevented']}")
        print(f"  Goals Conceded : {player_row['goalsConceded']}")

    # ── Discipline ──
    print(f"\n  🟨 DISCIPLINE:")
    print(f"  Yellow Cards : {player_row['yellowCards']}")
    print(f"  Red Cards    : {player_row['redCards']}")
    print(f"  Fouls        : {player_row['fouls']}")
    print(f"  Was Fouled   : {player_row['wasFouled']}")

    # ── Also pull info from the database ──
    print(f"\n  💾 DATABASE RECORD:")
    try:
        cursor = conn.cursor()
        # Search the DB player table for this player's name
        cursor.execute(
            "SELECT * FROM player WHERE player_name LIKE ?",
            (f"%{name}%",)
        )
        db_row = cursor.fetchone()

        if db_row:
            print(f"  DB ID          : {db_row[0]}")
            print(f"  DB Name        : {db_row[1]}")
            print(f"  DB Position    : {db_row[2]}")
            print(f"  Preferred Foot : {db_row[3]}")
            print(f"  Club (DB)      : {db_row[4]}")
            print(f"  Matches Played : {db_row[5]}")
            print(f"  Minutes (DB)   : {db_row[6]}")
            print(f"  Rating (DB)    : {db_row[7]:.3f}")
        else:
            print(f"  (Player not found in database)")

    except Exception as e:
        # If something goes wrong with the DB, just show the error message
        print(f"  (DB lookup error: {e})")

    print(f"{'=' * 55}\n")
