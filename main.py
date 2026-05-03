"""
main.py — Premier League 2025/26 Football Analytics
====================================================
Run this file to explore player and team stats interactively.
The program loads data from data.csv and football_data.db,
then lets you search, compare, and rank players and teams.
"""

# ─── IMPORTS ────────────────────────────────────────────────────────────────
import pandas as pd          # for working with the CSV data
import sqlite3               # for connecting to the database
import sys                   # for clean exit

# Import all our helper functions from logic.py
from logic import (
    load_data,
    find_player,
    best_striker,
    most_creative_player,
    best_defender,
    best_goalkeeper,
    team_table,
    show_player_profile
)


# ─── MENU DISPLAY ────────────────────────────────────────────────────────────
def show_menu():
    """Prints the main menu options to the screen."""
    print("\n" + "=" * 50)
    print(" PREMIER LEAGUE 2025/26 ANALYTICS")
    print("=" * 50)
    print("  1.  Best Striker")
    print("  2.  Most Creative Player")
    print("  3.  Best Defender")
    print("  4.  Best Goalkeeper")
    print("  5.  Team Table (goals, possession, performance)")
    print("  6.  Search Player Profile")
    print("  7.  Exit")
    print("=" * 50)


# ─── MAIN PROGRAM LOOP ───────────────────────────────────────────────────────
def main():
    """
    The main function — loads data once, then loops through the menu
    until the user decides to exit.
    """

    # Load the data once at the start so we don't reload it every time
    print("\n Loading data, please wait...")
    df, conn = load_data()
    print("Data loaded successfaully!\n")

    # Keep showing the menu until the user exits
    while True:
        show_menu() 

        # Ask the user to pick an option
        choice = input("\n Enter your choice (1-7): ").strip()

        # ── Option 1: Best Striker ──────────────────────────────────────────
        if choice == "1":
            print("\n TOP 10 STRIKERS (by goal contribution & rating):\n")
            result = best_striker(df)
            print(result.to_string(index=False))

        # ── Option 2: Most Creative Player ─────────────────────────────────
        elif choice == "2":
            print("\n TOP 10 MOST CREATIVE PLAYERS (by key passes, assists & chances created):\n")
            result = most_creative_player(df)
            print(result.to_string(index=False))

        # ── Option 3: Best Defender ─────────────────────────────────────────
        elif choice == "3":
            print("\n  TOP 10 BEST DEFENDERS (by tackles, interceptions & aerial duels):\n")
            result = best_defender(df)
            print(result.to_string(index=False))

        # ── Option 4: Best Goalkeeper ───────────────────────────────────────
        elif choice == "4":
            print("\n TOP 10 BEST GOALKEEPERS (by saves, clean sheets & goals prevented):\n")
            result = best_goalkeeper(df)
            print(result.to_string(index=False))

        # ── Option 5: Team Table ────────────────────────────────────────────
        elif choice == "5":
            print("\n TEAM TABLE — Avg Possession, Goals & Performance Score:\n")
            result = team_table(df)
            print(result.to_string(index=False))

        # ── Option 6: Player Profile Search ────────────────────────────────
        elif choice == "6":
            # Ask the user to type part of a player name
            search_term = input("\n Type a player name (or part of it): ").strip()

            if search_term == "":
                print(" lease enter at least one character.")
                continue

            # find_player does the fuzzy search and returns matches
            matches = find_player(df, search_term)

            if matches.empty:
                print(f" No players found matching '{search_term}'. Try a different name.")
                continue

            # If multiple players match, let the user pick the right one
            if len(matches) > 1:
                print(f"\n Found {len(matches)} players matching '{search_term}':\n")
                for i, row in matches.iterrows():
                    print(f"  [{list(matches.index).index(i) + 1}] {row['player_name']} — {row['team_name']} ({row['position']})")

                pick = input("\nEnter the number of the player you want: ").strip()

                # Check the user entered a valid number
                if not pick.isdigit() or int(pick) < 1 or int(pick) > len(matches):
                    print(" Invalid selection.")
                    continue

                # Select the chosen player row
                player_row = matches.iloc[int(pick) - 1]
            else:
                # Only one match — select it automatically
                player_row = matches.iloc[0]

            # Display the full player profile
            show_player_profile(player_row, conn)

        # ── Option 7: Exit ──────────────────────────────────────────────────
        elif choice == "7":
            print("\n Thanks for using the Premier League Analytics tool. Goodbye!\n")
            conn.close()   # close the database connection cleanly
            sys.exit()

        # ── Invalid input ───────────────────────────────────────────────────
        else:
            print(" That's not a valid option. Please enter a number between 1 and 7.")


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────
# This makes sure main() only runs when we run this file directly,
# not when it is imported somewhere else.
if __name__ == "__main__":
    main()
