# judge-panel-range

# US Figure Skating Judge Range Analysis

This script analyzes a judge’s scoring marks across all judged events in a given U.S. Figure Skating competition and summarizes how often that judge’s marks fall within or near the panel range.

I originally built it to automate a manual review process for judging patterns across multiple events. The underlying problem is straightforward in concept but tedious in practice: for each event in a competition, identify whether a given judge served on the panel, pull the detailed scoring page, and compare that judge’s GOEs and program components to the range of the rest of the panel.

## What the script does

Given:
- an official U.S. Figure Skating competition results page
- a judge’s full name

the script:

1. loops through each event in the competition
2. checks whether the judge participated in that event
3. pulls the judge detail scoring page
4. extracts each skater's GOE and component marks
5. calculates how often the judge’s marks were:
   - within the panel range
   - within the panel range ±1 for GOEs
   - within the panel range ±0.25 for components
6. exports a CSV file with:
   - skater-by-skater summaries
   - event totals
   - one block per event

## Example test case

Competition URL:
`https://ijs.usfigureskating.org/leaderboard/results/2025/36167/index.asp`

Judge:
`Rebecca Ye`

## Output

The script writes:

`judge_range_analysis.csv`

The output includes:
- an event header row
- row per skater
- an event summary row
- a blank spacer row between events

## Notes / assumptions

A few assumptions in the current version are specific to the U.S. Figure Skating IJS leaderboard format:

- the script depends on the current HTML structure of the leaderboard pages
- it assumes the final 3 score rows in each skater table are:
  - Composition
  - Presentation
  - Skating Skills
- it is intended as a practical analysis utility, not a production scraper

If the judging criteria (ie, more program components are introduced) or the site structure changes, the parsing logic may need to be updated.

## Dependencies

This script uses:
- pandas
- numpy
- requests
- beautifulsoup4
- lxml (as the parser used by BeautifulSoup)
