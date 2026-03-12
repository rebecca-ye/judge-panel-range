# -*- coding: utf-8 -*-
"""
Created on Mon Jul 14 13:51:32 2025

@author: Rebecca Ye

US Figure Skating judge range analysis script.

This script takes a competition URL and a judge's name, then:
1. Loops through each event in the competition
2. Checks whether the judge served on the panel
3. Pulls the judge detail page for that event
4. Computes how often the judge's GOEs/components fall within the panel range
5. Exports event-level and skater-level results to CSV

Sample test:
Competition URL:
https://ijs.usfigureskating.org/leaderboard/results/2025/36167/index.asp

Judge:
Rebecca Ye
"""

import re
import requests
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup


def find_officials_table(soup_event):
    """Find the officials table for an event page."""
    possible_classes = ["officials ladies", 
                        "officials men", 
                        "officials pairs", 
                        "officials team"]

    for table_class in possible_classes:
        tables = soup_event.find_all("table", {"class": table_class})
        if tables:
            return BeautifulSoup(str(tables), "html.parser")

    return None


def get_judge_info(soup_event, judge_name):
    """
    Return whether judge is on the panel, judge column label (e.g. J3),
    and total number of judges.
    """
    soup_judges = find_officials_table(soup_event)
    if soup_judges is None:
        return False, None, None

    tbody = soup_judges.find("tbody")
    if tbody is None:
        return False, None, None

    rows = tbody.find_all("tr")
    judges_dict = {
        row.find_all("td")[0].get_text(strip=True): row.find_all("td")[1].get_text(strip=True)
        for row in rows if len(row.find_all("td")) >= 2
    }

    judges_df = pd.DataFrame(judges_dict.items(), columns=["Function", "Name"])
    judges_df = judges_df.loc[judges_df["Function"].str.startswith("Judge")]

    for i in range(len(judges_df)):
        if judges_df.iloc[i]["Name"].startswith(judge_name):
            function = judges_df.iloc[i]["Function"]
            match = re.search(r"Judge (\d+)", function)
            if match:
                judge_col = "J" + match.group(1)
                num_judges = len(judges_df["Name"])
                return True, judge_col, num_judges

    return False, None, None


def get_judge_detail_soup(soup_event, base_url):
    """Return BeautifulSoup for the judge detail page."""
    details = soup_event.find_all("li", {"class": "judgeDetailRef"})
    if not details:
        return None

    soup_details = BeautifulSoup(str(details), "html.parser")
    link = soup_details.find("a", href=True)
    if link is None:
        return None

    detail_url = base_url + link["href"]
    response = requests.get(detail_url)
    return BeautifulSoup(response.text, "lxml")


def compute_skater_stats(df, judge_col, num_judges):
    """
    Compute range statistics for one skater.
    Assumes final 3 rows are components:
    Composition, Presentation, Skating Skills.
    """
    score_cols = [f"J{i}" for i in range(1, num_judges + 1)]
    raw_scores = df.loc[:, score_cols].dropna().reset_index(drop=True)

    # GOEs are all rows except the final 3 component rows
    raw_goes = raw_scores.iloc[:-3, :].replace("\u2013", "-")
    raw_goes.loc[raw_goes["J1"] == "-"] = np.nan
    raw_goes = raw_goes.astype(float)

    # Final 3 rows are components
    raw_comp = raw_scores.iloc[-3:, :].astype(float).reset_index(drop=True)

    min_goe = raw_goes.loc[:, raw_goes.columns != judge_col].min(axis=1).astype(float)
    max_goe = raw_goes.loc[:, raw_goes.columns != judge_col].max(axis=1).astype(float)

    min_comp = raw_comp.loc[:, raw_comp.columns != judge_col].min(axis=1).astype(float)
    max_comp = raw_comp.loc[:, raw_comp.columns != judge_col].max(axis=1).astype(float)

    num_goes = len(raw_scores) - 3
    total_goes = num_judges * num_goes
    total_components = num_judges * 3

    goes_in_range = 0
    goes_in_range_pm1 = 0
    for i in range(len(raw_goes)):
        if min_goe.iloc[i] <= raw_goes[judge_col].iloc[i] <= max_goe.iloc[i]:
            goes_in_range += 1
        if (min_goe.iloc[i] - 1) <= raw_goes[judge_col].iloc[i] <= (max_goe.iloc[i] + 1):
            goes_in_range_pm1 += 1

    comps_in_range = 0
    comps_in_range_pm25 = 0
    for i in range(3):
        if min_comp.iloc[i] <= raw_comp[judge_col].iloc[i] <= max_comp.iloc[i]:
            comps_in_range += 1
        if (min_comp.iloc[i] - 0.25) <= raw_comp[judge_col].iloc[i] <= (max_comp.iloc[i] + 0.25):
            comps_in_range_pm25 += 1

    stats = pd.DataFrame({
        "Number of Judges": [num_judges],
        "# of GOEs": [num_goes],
        "Total # GOEs": [total_goes],
        "# of GOEs w/in Range": [goes_in_range],
        "# of GOEs w/in Range +/- 1": [goes_in_range_pm1],
        "GOE % w/in Range": [str(round(goes_in_range / num_goes * 100)) + "%"],
        "GOE % w/in Range +/- 1": [str(round(goes_in_range_pm1 / num_goes * 100)) + "%"],
        "Panel Component Range": [None],
        "Composition": [str(min_comp.iloc[0]) + " - " + str(max_comp.iloc[0])],
        "Presentation": [str(min_comp.iloc[1]) + " - " + str(max_comp.iloc[1])],
        "Skating Skills": [str(min_comp.iloc[2]) + " - " + str(max_comp.iloc[2])],
        "TJ Component Range": [None],
        "TJ Composition": [raw_comp[judge_col].iloc[0]],
        "TJ Presentation": [raw_comp[judge_col].iloc[1]],
        "TJ Skating Skills": [raw_comp[judge_col].iloc[2]],
        "# of Components": [3],
        "Total # Components": [total_components],
        "# Components w/in Range": [comps_in_range],
        "# of Components w/in Range +/- .25": [comps_in_range_pm25],
        "Component % w/in Range": [str(round(comps_in_range / 3 * 100)) + "%"],
        "Component % w/in Range +/- .25": [str(round(comps_in_range_pm25 / 3 * 100)) + "%"]
    })

    return stats


def process_event(event_url, judge_name, base_url):
    """Process a single event if the judge is on the panel."""
    response = requests.get(event_url)
    soup_event = BeautifulSoup(response.text, "lxml")

    found, judge_col, num_judges = get_judge_info(soup_event, judge_name)
    if not found:
        return None

    soup_detail = get_judge_detail_soup(soup_event, base_url)
    if soup_detail is None:
        return None

    event_name_tag = soup_detail.find("h2", {"class": "catseg"})
    event_name = event_name_tag.get_text(strip=True) if event_name_tag else "Unknown Event"

    skater_name_tables = soup_detail.find_all("table", {"class": "sum"})
    skater_names = []
    for table in pd.read_html(str(skater_name_tables)):
        skater_names.append(table.iloc[0, 1].split(", ")[0])

    skater_tables = pd.read_html(str(soup_detail.find_all("table", {"class": "elm"})))

    stats_list = []
    for skater_df in skater_tables:
        try:
            stats_list.append(compute_skater_stats(skater_df, judge_col, num_judges))
        except Exception:
            # Skip malformed skater tables rather than failing entire event
            continue

    if not stats_list:
        return None

    stats = pd.concat(stats_list, ignore_index=True)
    stats.insert(0, "Number of Skaters", None)
    stats.insert(0, "Skater", skater_names[:len(stats)])

    summary = pd.DataFrame({
        "Skater": ["Event Totals"],
        "Number of Skaters": [None],
        "Number of Judges": [None],
        "# of GOEs": [stats["# of GOEs"].sum()],
        "Total # GOEs": [stats["Total # GOEs"].sum()],
        "# of GOEs w/in Range": [stats["# of GOEs w/in Range"].sum()],
        "# of GOEs w/in Range +/- 1": [stats["# of GOEs w/in Range +/- 1"].sum()],
        "GOE % w/in Range": [str(round(stats["# of GOEs w/in Range"].sum() / stats["# of GOEs"].sum() * 100, 2)) + "%"],
        "GOE % w/in Range +/- 1": [str(round(stats["# of GOEs w/in Range +/- 1"].sum() / stats["# of GOEs"].sum() * 100, 2)) + "%"],
        "Panel Component Range": [None],
        "Composition": [None],
        "Presentation": [None],
        "Skating Skills": [None],
        "TJ Component Range": [None],
        "TJ Composition": [None],
        "TJ Presentation": [None],
        "TJ Skating Skills": [None],
        "# of Components": [stats["# of Components"].sum()],
        "Total # Components": [stats["Total # Components"].sum()],
        "# Components w/in Range": [stats["# Components w/in Range"].sum()],
        "# of Components w/in Range +/- .25": [stats["# of Components w/in Range +/- .25"].sum()],
        "Component % w/in Range": [str(round(stats["# Components w/in Range"].sum() / stats["# of Components"].sum() * 100, 2)) + "%"],
        "Component % w/in Range +/- .25": [str(round(stats["# of Components w/in Range +/- .25"].sum() / stats["# of Components"].sum() * 100, 2)) + "%"]
    })

    stats = pd.concat([stats, summary], ignore_index=True)

    header = pd.DataFrame([{col: None for col in stats.columns}])
    header.loc[0, "Skater"] = event_name
    header.loc[0, "Number of Skaters"] = len(stats) - 1

    stats = pd.concat([header, stats], ignore_index=True)
    return stats


def main():
    comp_url = input("Enter competition results URL: ").strip()
    judge_name = input("Enter official's full name: ").strip()

    base_url = comp_url.replace("index.asp", "")

    response = requests.get(comp_url)
    soup = BeautifulSoup(response.text, "lxml")

    comp_table = soup.find("table", {"id": "daySort"})
    if comp_table is None:
        raise ValueError("Could not find competition table.")

    event_links = []
    for link in comp_table.find_all("a", href=True):
        event_links.append(base_url + link["href"])

    final = pd.DataFrame(columns=[
        "Skater", "Number of Skaters", "Number of Judges", "# of GOEs", "Total # GOEs",
        "# of GOEs w/in Range", "# of GOEs w/in Range +/- 1", "GOE % w/in Range",
        "GOE % w/in Range +/- 1", "Panel Component Range", "Composition", "Presentation",
        "Skating Skills", "TJ Component Range", "TJ Composition", "TJ Presentation",
        "TJ Skating Skills", "# of Components", "Total # Components", "# Components w/in Range",
        "# of Components w/in Range +/- .25", "Component % w/in Range",
        "Component % w/in Range +/- .25"
    ])

    for event_url in event_links:
        event_stats = process_event(event_url, judge_name, base_url)
        if event_stats is not None:
            print(event_stats)
            spacer = pd.DataFrame([{col: None for col in final.columns}])
            final = pd.concat([final, event_stats, spacer], ignore_index=True)

    final.to_csv("judge_range_analysis.csv", index=False)
    print("\nDone. Results saved to judge_range_analysis.csv")


if __name__ == "__main__":
    main()