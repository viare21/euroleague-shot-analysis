import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

from court_utils import draw_half_court

# ============================================================
# 0. PATHS (relative to the script, so the project runs on any PC)
# ============================================================

try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    BASE_DIR = os.getcwd()  # fallback when running cell-by-cell (F9) in Spyder

# CSVs live in a "csv_euroleague" folder at the same level as the project
DATA_DIR = os.path.join(BASE_DIR, "..", "csv_euroleague")

IMAGES_DIR = os.path.join(BASE_DIR, "images")
os.makedirs(IMAGES_DIR, exist_ok=True)

TEAM_ID = 'OLY'
SEASON = 'E2025'

# ============================================================
# 1. LOAD DATA
# ============================================================

points = pd.read_csv(os.path.join(DATA_DIR, "euroleague_points.csv"))
header = pd.read_csv(os.path.join(DATA_DIR, "euroleague_header.csv"))

# ============================================================
# 2. FILTER OLYMPIACOS GAMES, 2025-26 SEASON
# ============================================================

oly_header = header[
    (header['season_code'] == SEASON) &
    ((header['team_id_a'] == TEAM_ID) | (header['team_id_b'] == TEAM_ID))
].copy()

oly_header['venue'] = np.where(oly_header['team_id_a'] == TEAM_ID, 'Home', 'Away')

own_score = np.where(oly_header['team_id_a'] == TEAM_ID, oly_header['score_a'], oly_header['score_b'])
opp_score = np.where(oly_header['team_id_a'] == TEAM_ID, oly_header['score_b'], oly_header['score_a'])
oly_header['outcome'] = np.where(own_score > opp_score, 'Win', 'Loss')

print(f"Olympiacos games found: {len(oly_header)}")
print(oly_header['phase'].value_counts())
print(oly_header['outcome'].value_counts())

# ============================================================
# 3. FILTER SHOT DATA FOR OLYMPIACOS, MERGE VENUE/OUTCOME
# ============================================================

oly_shots = points[
    (points['game_id'].isin(oly_header['game_id'])) &
    (points['team_id'] == TEAM_ID)
].copy()

oly_shots = oly_shots.merge(
    oly_header[['game_id', 'venue', 'outcome']],
    on='game_id',
    how='left'
)

print(f"\nRows in the shot file for Olympiacos (free throws included): {len(oly_shots)}")

# ============================================================
# 4. CLEAN DATA: EXCLUDE FREE THROWS, FLAG MADE/MISSED
# ============================================================

# Free throws are logged as 'FTM' only (makes), with no separate attempt code,
# so they are excluded from the field goal analysis.
oly_field = oly_shots[oly_shots['action_id'] != 'FTM'].copy()

# Made or missed comes from the points column, shot type from the action code
oly_field['made'] = (oly_field['points'] > 0).astype(int)
oly_field['shot_type'] = 'unclear'
oly_field.loc[oly_field['action_id'].str.startswith('2'), 'shot_type'] = '2PT'
oly_field.loc[oly_field['action_id'].str.startswith('3'), 'shot_type'] = '3PT'

print(f"Field goal attempts: {len(oly_field)}")

# ============================================================
# 4.1 DATA QUALITY CHECKS
# ============================================================

print("\n=== Check 1: unclassified shot type and missing coordinates ===")
print(f"Unclear shot type: {(oly_field['shot_type'] == 'unclear').sum()}")
print(f"Missing (NaN) coordinates: {oly_field[['coord_x', 'coord_y']].isna().any(axis=1).sum()}")

no_coords = (oly_field['coord_x'] == 0) & (oly_field['coord_y'] == 0)  # (0, 0) is the basket itself: a placeholder
print(f"Placeholder coordinates (0, 0): {no_coords.sum()}")

print("\n=== Check 2: distance from the basket vs shot type ===")
oly_field['distance_cm'] = np.hypot(oly_field['coord_x'], oly_field['coord_y'])
three = oly_field.loc[oly_field['shot_type'] == '3PT', 'distance_cm']
two = oly_field.loc[oly_field['shot_type'] == '2PT', 'distance_cm']
print(f"3PT median distance: {three.median():.0f} cm | 2PT median distance: {two.median():.0f} cm")
print(f"3PT closer than 600 cm: {(three < 600).sum()} | 2PT farther than 700 cm: {(two > 700).sum()}")

print("\n=== Check 3: games by outcome (sample size) ===")
print(oly_field.groupby('outcome')['game_id'].nunique())

# Shots with placeholder coordinates cannot be placed on the court: drop them
oly_field = oly_field[~no_coords].copy()
print(f"\nField goal attempts used in the analysis: {len(oly_field)}")

# ============================================================
# 5. AGGREGATE STATISTICS (pooled: sum of makes / sum of attempts)
# ============================================================

def pct_table(df, by):
    out = df.groupby(by).agg(
        shots_attempted=('made', 'count'),
        shots_made=('made', 'sum')
    )
    out['percentage'] = (out['shots_made'] / out['shots_attempted'] * 100).round(1)
    return out

venue_stats = pct_table(oly_field, 'venue')
print("\n=== Shooting % by venue ===")
print(venue_stats)

outcome_stats = pct_table(oly_field, 'outcome')
print("\n=== Shooting % by outcome ===")
print(outcome_stats)

detailed_stats = pct_table(oly_field, ['outcome', 'shot_type'])
print("\n=== Shooting % by outcome and shot type ===")
print(detailed_stats)

shots_per_game = oly_field.groupby('outcome').agg(
    total_shots=('made', 'count'),
    games=('game_id', 'nunique')
)
shots_per_game['shots_per_game'] = (shots_per_game['total_shots'] / shots_per_game['games']).round(1)
print("\n=== Shots per game, by outcome ===")
print(shots_per_game)

# ============================================================
# 6. UNCERTAINTY: BOOTSTRAP OVER GAMES
# Shots in the same game are not independent, so the unit of resampling is the game.
# Wins and losses are resampled separately, then the gap in pooled FG% is computed.
# ============================================================

rng = np.random.default_rng(42)
N_BOOT = 5000

per_game = oly_field.groupby(['outcome', 'game_id', 'shot_type'])['made'].agg(['sum', 'count']).unstack('shot_type', fill_value=0)
per_game.columns = [f'{stat}_{shot}' for stat, shot in per_game.columns]
per_game['sum_all'] = per_game['sum_2PT'] + per_game['sum_3PT']
per_game['count_all'] = per_game['count_2PT'] + per_game['count_3PT']

def pooled_pct(games_df, shot):
    return games_df[f'sum_{shot}'].sum() / games_df[f'count_{shot}'].sum() * 100

wins_g = per_game.loc['Win']
loss_g = per_game.loc['Loss']

gaps = {'all': [], '2PT': [], '3PT': []}
for _ in range(N_BOOT):
    w = wins_g.iloc[rng.integers(0, len(wins_g), len(wins_g))]
    l = loss_g.iloc[rng.integers(0, len(loss_g), len(loss_g))]
    for shot in gaps:
        gaps[shot].append(pooled_pct(w, shot) - pooled_pct(l, shot))

print("\n=== Win minus loss gap in FG% (percentage points), bootstrap over games ===")
gap_summary = {}
for shot, values in gaps.items():
    point = pooled_pct(wins_g, shot) - pooled_pct(loss_g, shot)
    lo, hi = np.percentile(values, [2.5, 97.5])
    gap_summary[shot] = (point, lo, hi)
    print(f"{shot}: gap {point:+.1f}, 95% interval [{lo:+.1f}, {hi:+.1f}]")

# Difference between the 2PT gap and the 3PT gap
diff_values = np.array(gaps['2PT']) - np.array(gaps['3PT'])
diff_point = gap_summary['2PT'][0] - gap_summary['3PT'][0]
d_lo, d_hi = np.percentile(diff_values, [2.5, 97.5])
print(f"2PT gap minus 3PT gap: {diff_point:+.1f}, 95% interval [{d_lo:+.1f}, {d_hi:+.1f}]")

# ============================================================
# 7. SHOT ZONE BREAKDOWN (table only, no chart)
# Paint: x between -245 and 245, y between -157.5 and 580 - 157.5 (cm, basket at the origin)
# ============================================================

oly_field['zone'] = 'Other'
oly_field.loc[oly_field['shot_type'] == '3PT', 'zone'] = '3PT'

in_paint = (
    (oly_field['coord_x'].abs() <= 245) &
    (oly_field['coord_y'] >= -157.5) &
    (oly_field['coord_y'] <= 580 - 157.5)
)
oly_field.loc[(oly_field['shot_type'] == '2PT') & in_paint, 'zone'] = 'Paint'
oly_field.loc[(oly_field['shot_type'] == '2PT') & ~in_paint, 'zone'] = 'Mid-range'

print("\n=== Shot attempts by zone (% of total) ===")
zone_counts = oly_field['zone'].value_counts(normalize=True) * 100
print(zone_counts.round(1))

print("\n=== Shot attempts by zone, split by outcome (% within each outcome) ===")
zone_by_outcome = oly_field.groupby('outcome')['zone'].value_counts(normalize=True).unstack() * 100
print(zone_by_outcome.round(1))

# ============================================================
# 8. VISUAL STYLE SETTINGS (light palette, shared across all charts)
# ============================================================

BG_COLOR = '#FBFCEE'          # figure and axes background
BORDER_COLOR = '#D6DFA8'      # spines and grid
TEXT_COLOR = '#16233F'        # titles, labels, ticks
COURT_LINE_COLOR = '#5B6650'  # court lines
MADE_COLOR = '#3E8E4F'        # green
MISSED_COLOR = '#C6564F'      # coral
GOLD_COLOR = '#B8860B'        # gold

def style_axes(ax):
    """Applies the shared light style to a matplotlib axis."""
    ax.set_facecolor(BG_COLOR)
    ax.tick_params(colors=TEXT_COLOR)
    for spine in ax.spines.values():
        spine.set_color(BORDER_COLOR)

# ============================================================
# 9. SHOT CHART: WINS vs LOSSES
# ============================================================

plt.close('all')

fig_shotchart, axes = plt.subplots(1, 2, figsize=(16, 8))
fig_shotchart.patch.set_facecolor(BG_COLOR)

titles = {'Win': 'Wins', 'Loss': 'Losses'}

for ax, outcome_type in zip(axes, ['Win', 'Loss']):
    ax.set_facecolor(BG_COLOR)
    draw_half_court(ax, line_color=COURT_LINE_COLOR)

    subset = oly_field[oly_field['outcome'] == outcome_type]
    made = subset[subset['made'] == 1]
    missed = subset[subset['made'] == 0]

    ax.scatter(made['coord_x'] / 100, made['coord_y'] / 100, color=MADE_COLOR, alpha=0.6, s=25, label='Made')
    ax.scatter(missed['coord_x'] / 100, missed['coord_y'] / 100, color=MISSED_COLOR, alpha=0.6, s=25, label='Missed')

    ax.set_xlim(-8, 8)
    ax.set_ylim(-2, 13)
    ax.set_aspect('equal')
    ax.axis('off')

    legend = ax.legend(loc='upper right', facecolor=BG_COLOR, edgecolor=BORDER_COLOR)
    plt.setp(legend.get_texts(), color=TEXT_COLOR)

    ax.set_title(f'Olympiacos shots, {titles[outcome_type]} (2025-26 season)', color=TEXT_COLOR)

plt.tight_layout()
fig_shotchart.savefig(os.path.join(IMAGES_DIR, 'shot_chart_wins_losses.png'), dpi=150, facecolor=fig_shotchart.get_facecolor(), pad_inches=0.3)
plt.show()

# ============================================================
# 10. BAR CHART: SHOOTING % HOME vs AWAY
# ============================================================

fig_venue, ax = plt.subplots(figsize=(6, 5))
fig_venue.patch.set_facecolor(BG_COLOR)
style_axes(ax)

ax.bar(venue_stats.index, venue_stats['percentage'], color=[MADE_COLOR, GOLD_COLOR])
ax.set_ylabel('Shooting percentage (%)', color=TEXT_COLOR)
ax.set_title('Olympiacos shooting %, Home vs Away (2025-26)', color=TEXT_COLOR)
ax.set_ylim(0, 60)

for i, val in enumerate(venue_stats['percentage']):
    ax.text(i, val + 1, f'{val}%', ha='center', fontweight='bold', color=TEXT_COLOR)

plt.tight_layout()
fig_venue.savefig(os.path.join(IMAGES_DIR, 'shooting_pct_home_away.png'), dpi=150, facecolor=fig_venue.get_facecolor(), pad_inches=0.3)
plt.show()

# ============================================================
# 11. BAR CHART: SHOOTING % WIN vs LOSS
# ============================================================

fig_outcome, ax = plt.subplots(figsize=(6, 5))
fig_outcome.patch.set_facecolor(BG_COLOR)
style_axes(ax)

ax.bar(outcome_stats.index, outcome_stats['percentage'], color=[MISSED_COLOR, MADE_COLOR])
ax.set_ylabel('Shooting percentage (%)', color=TEXT_COLOR)
ax.set_title('Olympiacos shooting %, Wins vs Losses (2025-26)', color=TEXT_COLOR)
ax.set_ylim(30, 54)  # vertical axis does not start at zero, to make the gap readable

for i, val in enumerate(outcome_stats['percentage']):
    ax.text(i, val + 0.3, f'{val}%', ha='center', fontweight='bold', color=TEXT_COLOR)

plt.tight_layout()
fig_outcome.savefig(os.path.join(IMAGES_DIR, 'shooting_pct_win_loss.png'), dpi=150, facecolor=fig_outcome.get_facecolor(), pad_inches=0.3)
plt.show()

# ============================================================
# 12. BAR CHART: 2PT vs 3PT SHOOTING % BY OUTCOME
# ============================================================

pivot = detailed_stats['percentage'].unstack()
x = range(len(pivot))
width = 0.35

fig_2pt3pt, ax = plt.subplots(figsize=(7, 5))
fig_2pt3pt.patch.set_facecolor(BG_COLOR)
style_axes(ax)

bars1 = ax.bar([i - width/2 for i in x], pivot['2PT'], width, label='2PT', color=MADE_COLOR)
bars2 = ax.bar([i + width/2 for i in x], pivot['3PT'], width, label='3PT', color=GOLD_COLOR)

ax.set_xticks(x)
ax.set_xticklabels(pivot.index, color=TEXT_COLOR)
ax.set_ylabel('Shooting percentage (%)', color=TEXT_COLOR)
ax.set_title('Olympiacos: 2PT vs 3PT shooting % by outcome', color=TEXT_COLOR)
ax.set_ylim(20, 68)  # vertical axis does not start at zero, to make the gaps readable

legend = ax.legend(facecolor=BG_COLOR, edgecolor=BORDER_COLOR)
plt.setp(legend.get_texts(), color=TEXT_COLOR)

for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, height + 0.6, f'{height}%', ha='center', fontweight='bold', color=TEXT_COLOR)

plt.tight_layout()
fig_2pt3pt.savefig(os.path.join(IMAGES_DIR, 'shooting_pct_2pt_3pt.png'), dpi=150, facecolor=fig_2pt3pt.get_facecolor(), pad_inches=0.3)
plt.show()
