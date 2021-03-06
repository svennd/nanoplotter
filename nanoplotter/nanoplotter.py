# wdecoster
"""
This module provides functions for plotting data extracted from Oxford Nanopore sequencing
reads and alignments, but some of it's functions can also be used for other applications.


FUNCTIONS
* Check if a specified color is a valid matplotlib color
checkvalidColor(color)
* Check if a specified output format is valid
checkvalidFormat(format)
* Create a bivariate plot with dots, hexbins and/or kernel density estimates.
Also arguments for specifying axis names, color and xlim/ylim
scatter(x, y, names, path, color, format, plots, stat=None, log=False, minvalx=0, minvaly=0)
* Create cumulative yield plot and evaluate read length and quality over time
timePlots(df, path, color, format)
* Create length distribution histogram and density curve
lengthPlots(array, name, path, n50, color, format, log=False)
* Create flowcell physical layout in numpy array
makeLayout()
* Present the activity (number of reads) per channel on the flowcell as a heatmap
spatialHeatmap(array, title, path, color, format)

"""


import logging
import sys
from datetime import timedelta
import pandas as pd
import numpy as np
import base64
from math import ceil
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import colors as mcolors
import seaborn as sns
from pauvre.marginplot import margin_plot


class Plot(object):
    """A Plot object is defined by a path to the output file and the title of the plot."""

    def __init__(self, path, title):
        self.path = path
        self.title = title

    def encode(self):
        """Return the base64 encoding of the plot and insert in html image tag."""
        data_uri = base64.b64encode(open(self.path, 'rb').read()).decode('utf-8').replace('\n', '')
        return '<img src="data:image/png;base64,{0}">'.format(data_uri)


def check_valid_color(color):
    """Check if the color provided by the user is valid.

    If color is invalid the default is returned.
    """
    if color in list(mcolors.CSS4_COLORS.keys()) + ["#4CB391"]:
        logging.info("Nanoplotter: Valid color {}.".format(color))
        return color
    else:
        logging.info("Nanoplotter: Invalid color {}, using default.".format(color))
        sys.stderr.write("Invalid color {}, using default.\n".format(color))
        return "#4CB391"


def check_valid_format(figformat):
    """Check if the specified figure format is valid.

    If format is invalid the default is returned.
    Probably installation-dependent
    """
    fig = plt.figure()
    if figformat in list(fig.canvas.get_supported_filetypes().keys()):
        logging.info("Nanoplotter: valid output format {}".format(figformat))
        return figformat
    else:
        logging.info("Nanoplotter: invalid output format {}".format(figformat))
        sys.stderr.write("Invalid format {}, using default.\n".format(figformat))
        return "png"


def scatter(x, y, names, path, plots, color="#4CB391", figformat="png", stat=None, log=False, minvalx=0, minvaly=0):
    """Create bivariate plots.

    Create four types of bivariate plots of x vs y, containing marginal summaries
    -A scatter plot with histograms on axes
    -A hexagonal binned plot with histograms on axes
    -A kernel density plot with density curves on axes, subsampled to 10000 reads if required
    -A pauvre-style plot using code from https://github.com/conchoecia/pauvre
    """
    logging.info("Nanoplotter: Creating {} vs {} plots using statistics from {} reads.".format(
        names[0], names[1], x.size))
    sns.set(style="ticks")
    maxvalx = np.amax(x)
    maxvaly = np.amax(y)

    plots_made = []

    if plots["hex"]:
        hex_plot = Plot(
            path=path + "_hex." + figformat,
            title="{} vs {} plot using hexagonal bins".format(names[0], names[1]))
        plot = sns.jointplot(
            x=x,
            y=y,
            kind="hex",
            color=color,
            stat_func=stat,
            space=0,
            xlim=(minvalx, maxvalx),
            ylim=(minvaly, maxvaly),
            size=10)
        plot.set_axis_labels(names[0], names[1])
        if log:
            hex_plot.title = hex_plot.title + " after log transformation of read lengths"
            ticks = [10**i for i in range(10) if not 10**i > 10 * (10**maxvalx)]
            plot.ax_joint.set_xticks(np.log10(ticks))
            plot.ax_joint.set_xticklabels(ticks)
        plot.savefig(hex_plot.path, format=figformat, dpi=100)
        plots_made.append(hex_plot)

    sns.set(style="darkgrid")
    if plots["dot"]:
        dot_plot = Plot(
            path=path + "_dot." + figformat,
            title="{} vs {} plot using dots".format(names[0], names[1]))
        plot = sns.jointplot(
            x=x,
            y=y,
            kind="scatter",
            color=color,
            stat_func=stat,
            xlim=(minvalx, maxvalx),
            ylim=(minvaly, maxvaly),
            space=0,
            size=10,
            joint_kws={"s": 1})
        plot.set_axis_labels(names[0], names[1])
        if log:
            dot_plot.title = dot_plot.title + " after log transformation of read lengths"
            ticks = [10**i for i in range(10) if not 10**i > 10 * (10**maxvalx)]
            plot.ax_joint.set_xticks(np.log10(ticks))
            plot.ax_joint.set_xticklabels(ticks)
        plot.savefig(dot_plot.path, format=figformat, dpi=100)
        plots_made.append(dot_plot)

    if plots["kde"]:
        kde_plot = Plot(
            path=path + "_kde." + figformat,
            title="{} vs {} plot using a kernel density estimation".format(names[0], names[1]))
        plot = sns.jointplot(
            x=x,
            y=y,
            kind="kde",
            clip=((0, np.Inf), (0, np.Inf)),
            xlim=(minvalx, maxvalx),
            ylim=(minvaly, maxvaly),
            space=0,
            color=color,
            stat_func=stat,
            shade_lowest=False,
            size=10)
        plot.set_axis_labels(names[0], names[1])
        if log:
            kde_plot.title = kde_plot.title + " after log transformation of read lengths"
            ticks = [10**i for i in range(10) if not 10**i > 10 * (10**maxvalx)]
            plot.ax_joint.set_xticks(np.log10(ticks))
            plot.ax_joint.set_xticklabels(ticks)
        plot.savefig(kde_plot.path, format=figformat, dpi=100)
        plots_made.append(kde_plot)

    if plots["pauvre"] and names == ['Read lengths', 'Average read quality']:
        pauvre_plot = Plot(
            path=path + "_pauvre." + figformat,
            title="{} vs {} plot using pauvre-style @conchoecia".format(names[0], names[1]))
        sns.set_style("white")
        margin_plot(df=pd.DataFrame({"length": x, "meanQual": y}),
                    Y_AXES=False,
                    title="Length vs Quality",
                    plot_maxlen=None,
                    plot_minlen=0,
                    plot_maxqual=None,
                    plot_minqual=0,
                    lengthbin=None,
                    qualbin=None,
                    BASENAME="whatever",
                    path=pauvre_plot.path,
                    fileform=[figformat],
                    dpi=600,
                    TRANSPARENT=True,
                    QUIET=True)
        if log:
            pauvre_plot.title = pauvre_plot.title + " after log transformation of read lengths"
        plots_made.append(pauvre_plot)
    plt.close("all")
    return plots_made


def check_valid_time_and_sort(df, timescol, days=5):
    """Check if the data contains reads created within the same `days` timeframe.

    if not, print warning and only return part of the data which is within `days` days
    """
    timediff = (df[timescol].max() - df[timescol].min()).days
    if timediff < days:
        return df.sort_values(timescol)
    else:
        sys.stderr.write("\nWarning: data generated is from more than {} days.\n".format(str(days)))
        sys.stderr.write("Likely this indicates you are combining multiple runs.\n")
        sys.stderr.write(
            "Plots based on time are invalid and therefore truncated to first {} days.\n\n".format(
                str(days)))
        logging.warning("Time plots truncated to first {} days: invalid timespan: {} days".format(
            str(days), str(timediff)))
        return df[df[timescol] < timedelta(days=days)].sort_values(timescol)


def time_plots(df, path, color="#4CB391", figformat="png"):
    """Making plots of time vs read length, time vs quality and cumulative yield."""
    dfs = check_valid_time_and_sort(df, "start_time")
    logging.info("Nanoplotter: Creating timeplots using {} reads.".format(len(dfs)))
    dfs["cumyield_gb"] = dfs["lengths"].cumsum() / 10**9
    dfs_sparse = dfs.sample(min(2000, len(df.index)))
    dfs_sparse["start_time"] = dfs_sparse["start_time"].astype('timedelta64[s]')  # ?! dtype float64
    maxtime = dfs_sparse["start_time"].max()
    if maxtime < 72 * 3600:
        steps = 4
    else:
        steps = 8
    ticks = [int(i) for i in range(0, 168, steps) if not i > (maxtime / 3600)]

    time_length = Plot(
        path=path + "TimeLengthScatterPlot." + figformat,
        title="Scatter plot of read length over time")
    g = sns.JointGrid(
        x='start_time',
        y="lengths",
        data=dfs_sparse,
        space=0,
        size=10,
        xlim=(0, maxtime))
    g.plot_joint(plt.scatter, color=color)
    g.ax_joint.set_xticks([i * 3600 for i in ticks])
    g.ax_joint.set_xticklabels(ticks)
    g.ax_marg_y.hist(dfs_sparse["lengths"].dropna(), orientation="horizontal", color=color)
    g.set_axis_labels('Run time (hours)', 'Median read length')
    g.savefig(
        fname=time_length.path,
        format=figformat,
        dpi=100)
    plt.close("all")

    cum_yield = Plot(
        path=path + "CumulativeYieldPlot." + figformat,
        title="Cumulative yield")
    ax = sns.regplot(
        x='start_time',
        y="cumyield_gb",
        data=dfs_sparse,
        x_ci=None,
        fit_reg=False,
        color=color,
        scatter_kws={"s": 5})
    ax.set(
        xticks=[i * 3600 for i in ticks],
        xticklabels=ticks,
        xlabel='Run time (hours)',
        ylabel='Cumulative yield in gigabase')
    fig = ax.get_figure()
    fig.savefig(cum_yield.path, format=figformat, dpi=100)
    plt.close("all")

    plots = [cum_yield, time_length]

    if "quals" in dfs:
        time_qual = Plot(
            path=path + "TimeQualityViolinPlot." + figformat,
            title="Violin plot of quality over time")
        sns.set_style("white")
        dfs['timebin'] = pd.cut(
            x=dfs["start_time"],
            bins=ceil((maxtime / 3600) / 6),
            labels=[str(i) + "-" + str(i + 6) for i in range(0, 168, 6) if not i > (maxtime / 3600)])
        ax = sns.violinplot(
            x="timebin",
            y="quals",
            data=dfs,
            inner=None,
            cut=0,
            linewidth=0)
        ax.set(
            xlabel='Interval (hours)',
            ylabel="Basecall quality")
        plt.xticks(rotation=30)
        fig = ax.get_figure()
        fig.savefig(
            fname=time_qual.path,
            format=figformat,
            dpi=100,
            bbox_inches='tight')
        plots.append(time_qual)
    return plots


def length_plots(array, name, path, n50=None, color="#4CB391", figformat="png"):
    """Create histogram of normal and log transformed read lengths."""
    logging.info("Nanoplotter: Creating length plots for {}.".format(name))
    maxvalx = np.amax(array)
    if n50:
        logging.info("Nanoplotter: Using {} reads with read length N50 of {}bp and maximum of {}bp.".format(
            array.size, n50, maxvalx))
    else:
        logging.info("Nanoplotter: Using {} reads maximum of {}bp.".format(array.size, maxvalx))
    histogram = Plot(
        path=path + "Histogram" + name.replace(' ', '') + "." + figformat,
        title="Histogram of read lengths")
    ax = sns.distplot(
        a=array,
        kde=False,
        hist=True,
        bins=round(int(maxvalx) / 100),
        color=color)
    if n50:
        plt.axvline(n50)
        plt.annotate('N50', xy=(n50, np.amax([h.get_height() for h in ax.patches])), size=8)
    ax.set(xlabel='Read length', ylabel='Number of reads')
    fig = ax.get_figure()
    fig.savefig(histogram.path, format=figformat, dpi=100)
    plt.close("all")

    log_histogram = Plot(
        path=path + "LogTransformedHistogram" + name.replace(' ', '') + "." + figformat,
        title="Histogram of read lengths after log transformation")
    ax = sns.distplot(
        a=np.log10(array),
        kde=False,
        hist=True,
        color=color)
    ticks = [10**i for i in range(10) if not 10**i > 10 * maxvalx]
    ax.set(
        xticks=np.log10(ticks),
        xticklabels=ticks)
    if n50:
        plt.axvline(np.log10(n50))
        plt.annotate('N50', xy=(np.log10(n50), np.amax(
            [h.get_height() for h in ax.patches])), size=8)
    ax.set(xlabel='Read length', ylabel='Number of reads')
    fig = ax.get_figure()
    fig.savefig(log_histogram.path, format=figformat, dpi=100)
    plt.close("all")
    return [histogram, log_histogram]


def make_layout():
    """Make the physical layout of the MinION flowcell.

    based on https://bioinformatics.stackexchange.com/a/749/681
    returned as a numpy array
    """
    layoutlist = []
    for i, j in zip([33, 481, 417, 353, 289, 225, 161, 97], [8, 456, 392, 328, 264, 200, 136, 72]):
        for n in range(4):
            layoutlist.append(list(range(i + n * 8, (i + n * 8) + 8, 1)) +
                              list(range(j + n * 8, (j + n * 8) - 8, -1)))
    return np.array(layoutlist).transpose()


def spatial_heatmap(array, title, path, color="Greens", figformat="png"):
    """Taking channel information and creating post run channel activity plots."""
    logging.info("Nanoplotter: Creating activity map for {} using statistics from {} reads.".format(
        title.lower(), array.size))
    activity_map = Plot(
        path=path + "." + figformat,
        title="Channel activity")
    layout = make_layout()
    activityData = np.zeros((16, 32))
    valueCounts = pd.value_counts(pd.Series(array))
    for entry in valueCounts.keys():
        activityData[np.where(layout == entry)] = valueCounts[entry]
    plt.figure()
    ax = sns.heatmap(
        data=activityData,
        xticklabels=range(1, 33),
        yticklabels=range(1, 17),
        square=True,
        cbar_kws={"orientation": "horizontal"},
        cmap=color,
        linewidths=0.20)
    ax.set_title(title)
    fig = ax.get_figure()
    fig.savefig(activity_map.path, format=figformat, dpi=100)
    plt.close("all")
    return [activity_map]


def violin_or_box_plot(df, y, figformat, path, violin=True, log=False):
    """Create a violin or boxplot from the received DataFrame.

    The x-axis should be divided based on the 'dataset' column,
    the y-axis is specified in the arguments
    """
    if violin:
        logging.info("Nanoplotter: Creating violin plot for {}.".format(y))
        ax = sns.violinplot(
            x="dataset",
            y=y,
            data=df,
            inner=None,
            cut=0,
            order=df["dataset"].unique(),
            linewidth=0)
    else:
        logging.info("Nanoplotter: Creating box plot for {}.".format(y))
        ax = sns.boxplot(
            x="dataset",
            y=y,
            data=df,
            order=df["dataset"].unique())
    if log:
        ticks = [10**i for i in range(10) if not 10**i > 10 * (10**np.amax(df[y]))]
        ax.set(
            yticks=np.log10(ticks),
            yticklabels=ticks)
    plt.xticks(rotation=30)
    fig = ax.get_figure()
    fig.savefig(
        fname=path + "NanoComp_" + y.replace(' ', '_') + '.' + figformat,
        format=figformat,
        dpi=100,
        bbox_inches='tight')
    plt.close("all")


def output_barplot(df, figformat, path):
    """Create barplots based on number of reads and total sum of nucleotides sequenced."""
    ax = sns.countplot(
        x="dataset",
        data=df,
        order=df["dataset"].unique())
    ax.set(xlabel='Number of reads')
    plt.xticks(rotation=30)
    fig = ax.get_figure()
    fig.savefig(
        fname=path + "NanoComp_number_of_reads." + figformat,
        format=figformat,
        dpi=100,
        bbox_inches='tight')
    plt.close("all")

    ax = sns.barplot(
        x=df["dataset"].unique(),
        y=df.groupby('dataset')['lengths'].sum() / 1e6,
        order=df["dataset"].unique())
    ax.set(ylabel='Total megabase sequenced')
    plt.xticks(rotation=30)
    fig = ax.get_figure()
    fig.savefig(
        fname=path + "NanoComp_total_throughput." + figformat,
        format=figformat,
        dpi=100,
        bbox_inches='tight')
    plt.close("all")


def run_tests():
    import pickle
    df = pickle.load(open("nanotest/sequencing_summary.pickle", "rb"))
    scatter(
        x=df["lengths"],
        y=df["quals"],
        names=['Read lengths', 'Average read quality'],
        path="LengthvsQualityScatterPlot",
        plots={'dot': 1, 'kde': 1, 'hex': 1, 'pauvre': 1})
    time_plots(
        df=df,
        path=".",
        color="#4CB391")
    length_plots(
        array=df["lengths"],
        name="lengths",
        path=".")
    spatial_heatmap(
        array=df["channelIDs"],
        title="Number of reads generated per channel",
        path="ActivityMap_ReadsPerChannel")


checkvalidColor = check_valid_color
checkvalidFormat = check_valid_format
spatialHeatmap = spatial_heatmap
lengthPlots = length_plots
timePlots = time_plots


if __name__ == "__main__":
    run_tests()
