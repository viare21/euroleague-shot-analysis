import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


def draw_half_court(ax, line_width=1.5, line_color='black'):
    """
    Draws a basketball half-court using FIBA dimensions, in meters,
    with the basket centered at (0,0).
    """
    # corner 3pt lines
    ax.plot([-6.6, -6.6], [-1.575, 0], linewidth=line_width, color=line_color)
    ax.plot([6.6, 6.6], [-1.575, 0], linewidth=line_width, color=line_color)

    # 3pt arc
    ax.add_artist(mpatches.Arc((0, 0), 6.6*2, 6.6*2, theta1=0, theta2=180, linewidth=line_width, edgecolor=line_color))

    # lane and key
    ax.plot([-2.45, -2.45], [-1.575, -1.575 + 5.8], linewidth=line_width, color=line_color)
    ax.plot([2.45, 2.45], [-1.575, -1.575 + 5.8], linewidth=line_width, color=line_color)
    ax.plot([-2.45, 2.45], [-1.575 + 5.8, -1.575 + 5.8], linewidth=line_width, color=line_color)
    ax.add_artist(mpatches.Arc((0, -1.575 + 5.8), 3.6, 3.6, theta1=0, theta2=180, linewidth=line_width, edgecolor=line_color))

    # rim
    ax.add_artist(mpatches.Circle((0, 0), 0.3, facecolor='none', linewidth=line_width, edgecolor=line_color))
    ax.plot([-0.9, 0.9], [-1.575 + 1.2, -1.575 + 1.2], linewidth=line_width, color=line_color)

    # base line
    ax.plot([-7.5, 7.5], [-1.575, -1.575], linewidth=line_width, color=line_color)

    # center line and arc
    ax.plot([-7.5, 7.5], [-1.575 + 14, -1.575 + 14], linewidth=line_width, color=line_color)
    ax.add_artist(mpatches.Arc((0, -1.575 + 14), 3.6, 3.6, theta1=0, theta2=180, linewidth=line_width, edgecolor=line_color))

    # side lines
    ax.plot([-7.5, -7.5], [-1.575, -1.575 + 14], linewidth=line_width, color=line_color)
    ax.plot([7.5, 7.5], [-1.575, -1.575 + 14], linewidth=line_width, color=line_color)