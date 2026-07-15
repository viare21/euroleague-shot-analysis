import pandas as pd
import matplotlib.pyplot as plt

import os

os.makedirs("images", exist_ok=True)
os.chdir(r"C:\Users\Bologna\Desktop\anaconda")
print(os.getcwd())

from court_utils import draw_half_court


# ============================================================
# 1. LOAD DATA
# ============================================================

points = pd.read_csv("euroleague_points.csv")
header = pd.read_csv("euroleague_header.csv")
teams = pd.read_csv("euroleague_teams.csv")

print("=== POINTS (shot data) ===")
print(points.shape)
print(points.columns.tolist())

print("\n=== HEADER (game metadata) ===")
print(header.shape)
print(header.columns.tolist())

print("\n=== TEAMS ===")
print(teams.shape)
print(teams.columns.tolist())

# ============================================================
# 2. FILTER OLYMPIACOS GAMES, 2025-26 SEASON
# ============================================================

oly_header = header[
    (header['season_code'] == 'E2025') &
    ((header['team_id_a'] == 'OLY') | (header['team_id_b'] == 'OLY'))
].copy()

print(f"\nOlympiacos games found: {len(oly_header)}")

oly_header['venue'] = oly_header.apply(
    lambda row: 'Home' if row['team_id_a'] == 'OLY' else 'Away', axis=1
)

def get_outcome(row):
    if row['team_id_a'] == 'OLY':
        return 'Win' if row['score_a'] > row['score_b'] else 'Loss'
    else:
        return 'Win' if row['score_b'] > row['score_a'] else 'Loss'

oly_header['outcome'] = oly_header.apply(get_outcome, axis=1)

print(oly_header[['game_id', 'game', 'team_a', 'team_b', 'score_a', 'score_b', 'venue', 'outcome']].head(10))

# ============================================================
# 3. FILTER SHOT DATA FOR OLYMPIACOS, MERGE VENUE/OUTCOME
# ============================================================

oly_shots = points[
    (points['game_id'].isin(oly_header['game_id'])) &
    (points['team_id'] == 'OLY')
].copy()

oly_shots = oly_shots.merge(
    oly_header[['game_id', 'venue', 'outcome']],
    on='game_id',
    how='left'
)

print(oly_shots.shape)
print(oly_shots['action_id'].unique())

# ============================================================
# 4. CLEAN DATA: EXCLUDE FREE THROWS, FLAG MADE/MISSED
# ============================================================

oly_field = oly_shots[oly_shots['action_id'] != 'FTM'].copy()
oly_field['made'] = oly_field['action_id'].str.contains('FGM').astype(int)
oly_field['shot_type'] = oly_field['action_id'].str[0] + 'PT'

# ============================================================
# 5. AGGREGATE STATISTICS
# ============================================================

# Shooting % by venue
venue_stats = oly_field.groupby('venue').agg(
    shots_attempted=('made', 'count'),
    shots_made=('made', 'sum')
)
venue_stats['percentage'] = (venue_stats['shots_made'] / venue_stats['shots_attempted'] * 100).round(1)
print("\n=== Shooting % by venue ===")
print(venue_stats)

# Shooting % by outcome
outcome_stats = oly_field.groupby('outcome').agg(
    shots_attempted=('made', 'count'),
    shots_made=('made', 'sum')
)
outcome_stats['percentage'] = (outcome_stats['shots_made'] / outcome_stats['shots_attempted'] * 100).round(1)
print("\n=== Shooting % by outcome ===")
print(outcome_stats)

# Shooting % by outcome AND shot type (2PT/3PT)
detailed_stats = oly_field.groupby(['outcome', 'shot_type']).agg(
    shots_attempted=('made', 'count'),
    shots_made=('made', 'sum')
)
detailed_stats['percentage'] = (detailed_stats['shots_made'] / detailed_stats['shots_attempted'] * 100).round(1)
print("\n=== Shooting % by outcome and shot type ===")
print(detailed_stats)

# Shots per game, by outcome (sanity check: volume vs efficiency)
shots_per_game = oly_field.groupby('outcome').agg(
    total_shots=('made', 'count'),
    games=('game_id', 'nunique')
)
shots_per_game['shots_per_game'] = (shots_per_game['total_shots'] / shots_per_game['games']).round(1)
print("\n=== Shots per game, by outcome ===")
print(shots_per_game)

# ============================================================
# 6. VISUAL STYLE SETTINGS (shared across all charts)
# ============================================================

BG_COLOR = '#0a1f3d'       # dark navy background
COURT_LINE_COLOR = '#FFD580'  # light orange/yellow
MADE_COLOR = '#90EE90'     # light green
MISSED_COLOR = '#FF7F7F'   # light red

def style_dark_axes(ax):
    """Applies the shared dark navy style to a matplotlib axis."""
    ax.set_facecolor(BG_COLOR)
    ax.tick_params(colors='white')
    for spine in ax.spines.values():
        spine.set_color('white')

# ============================================================
# 7. SHOT CHART: WINS vs LOSSES
# ============================================================

plt.close('all')

fig, axes = plt.subplots(1, 2, figsize=(16, 8))
fig.patch.set_facecolor(BG_COLOR)

titles = {'Win': 'Wins', 'Loss': 'Losses'}

for ax, outcome_type in zip(axes, ['Win', 'Loss']):
    ax.set_facecolor(BG_COLOR)
    draw_half_court(ax, line_color=COURT_LINE_COLOR)

    subset = oly_field[oly_field['outcome'] == outcome_type]
    made = subset[subset['made'] == 1]
    missed = subset[subset['made'] == 0]

    ax.scatter(made['coord_x'] / 100, made['coord_y'] / 100, color=MADE_COLOR, alpha=0.7, s=25, label='Made')
    ax.scatter(missed['coord_x'] / 100, missed['coord_y'] / 100, color=MISSED_COLOR, alpha=0.7, s=25, label='Missed')

    ax.set_xlim(-8, 8)
    ax.set_ylim(-2, 13)
    ax.set_aspect('equal')
    ax.axis('off')

    legend = ax.legend(loc='upper right', facecolor=BG_COLOR, edgecolor=COURT_LINE_COLOR)
    plt.setp(legend.get_texts(), color='white')

    ax.set_title(f'Olympiacos shots — {titles[outcome_type]} (2025-26 season)', color='white')

plt.tight_layout()
plt.savefig('images/shot_chart_wins_losses.png', dpi=150, facecolor=fig.get_facecolor(), pad_inches=0.3)
plt.show()

from PIL import Image
img = Image.open('images/shot_chart_wins_losses.png')
colors = img.getcolors(maxcolors=100000)
print(f"Numero di colori distinti: {len(colors)}")
print(colors[:10])  # mostra i 10 colori più comuni

# ============================================================
# 8. BAR CHART: SHOOTING % HOME vs AWAY
# ============================================================

fig, ax = plt.subplots(figsize=(6, 5))
fig.patch.set_facecolor(BG_COLOR)
style_dark_axes(ax)

ax.bar(venue_stats.index, venue_stats['percentage'], color=[MADE_COLOR, COURT_LINE_COLOR])
ax.set_ylabel('Shooting percentage (%)', color='white')
ax.set_title('Olympiacos shooting % — Home vs Away (2025-26)', color='white')
ax.set_ylim(0, 60)

for i, val in enumerate(venue_stats['percentage']):
    ax.text(i, val + 1, f'{val}%', ha='center', fontweight='bold', color='white')

plt.tight_layout()
plt.savefig('images/shooting_pct_home_away.png', dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
plt.show()

# ============================================================
# 9. BAR CHART: SHOOTING % WIN vs LOSS
# ============================================================

fig, ax = plt.subplots(figsize=(6, 5))
fig.patch.set_facecolor(BG_COLOR)
style_dark_axes(ax)

ax.bar(outcome_stats.index, outcome_stats['percentage'], color=[MISSED_COLOR, MADE_COLOR])
ax.set_ylabel('Shooting percentage (%)', color='white')
ax.set_title('Olympiacos shooting % — Wins vs Losses (2025-26)', color='white')
ax.set_ylim(0, 60)

for i, val in enumerate(outcome_stats['percentage']):
    ax.text(i, val + 1, f'{val}%', ha='center', fontweight='bold', color='white')

plt.tight_layout()
plt.savefig('images/shooting_pct_win_loss.png', dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
plt.show()

# ============================================================
# 10. BAR CHART: 2PT vs 3PT SHOOTING % BY OUTCOME
# ============================================================

pivot = detailed_stats['percentage'].unstack()
x = range(len(pivot))
width = 0.35

fig, ax = plt.subplots(figsize=(7, 5))
fig.patch.set_facecolor(BG_COLOR)
style_dark_axes(ax)

bars1 = ax.bar([i - width/2 for i in x], pivot['2PT'], width, label='2PT', color=MADE_COLOR)
bars2 = ax.bar([i + width/2 for i in x], pivot['3PT'], width, label='3PT', color=COURT_LINE_COLOR)

ax.set_xticks(x)
ax.set_xticklabels(pivot.index, color='white')
ax.set_ylabel('Shooting percentage (%)', color='white')
ax.set_title('Olympiacos: 2PT vs 3PT shooting % by outcome', color='white')

legend = ax.legend(facecolor=BG_COLOR, edgecolor='white')
plt.setp(legend.get_texts(), color='white')

for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, height + 0.5, f'{height}%', ha='center', fontweight='bold', color='white')

plt.tight_layout()
plt.savefig('images/shooting_pct_2pt_3pt.png', dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
plt.show()

################################################################
# Rough mid-range zone: outside the paint, inside the 3pt line
# Paint boundaries (in cm, matching coord_x/coord_y): x between -245 and 245, y between -157.5 and 580-157.5
# We already know it's a 2PT shot (not FTM, not 3PT)

oly_field['zone'] = 'Other'
oly_field.loc[oly_field['shot_type'] == '3PT', 'zone'] = '3PT'

in_paint = (
    (oly_field['coord_x'].abs() <= 245) &
    (oly_field['coord_y'] >= -157.5) &
    (oly_field['coord_y'] <= 580 - 157.5)
)
oly_field.loc[(oly_field['shot_type'] == '2PT') & in_paint, 'zone'] = 'Paint'
oly_field.loc[(oly_field['shot_type'] == '2PT') & ~in_paint, 'zone'] = 'Mid-range'

zone_counts = oly_field['zone'].value_counts(normalize=True) * 100
print(zone_counts.round(1))

#####################################################################

zone_by_outcome = oly_field.groupby('outcome')['zone'].value_counts(normalize=True).unstack() * 100
print(zone_by_outcome.round(1))

plt.savefig('images/shot_chart_wins_losses.png', dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())