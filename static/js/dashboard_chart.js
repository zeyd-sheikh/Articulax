const scoreHistoryDataNode = document.getElementById("score_history_data");
const scoreChartSvg = document.getElementById("score_chart_svg");
const scoreChartEmpty = document.getElementById("score_chart_empty");

function parseScoreHistory() {
    if (!scoreHistoryDataNode) {
        return [];
    }

    try {
        const parsed = JSON.parse(scoreHistoryDataNode.textContent || "[]");
        if (!Array.isArray(parsed)) {
            return [];
        }
        return parsed
            .map((item) => ({
                ...item,
                score: Number(item.score),
            }))
            .filter((item) => Number.isFinite(item.score));
    } catch (error) {
        return [];
    }
}

function createSvgEl(tag, attrs) {
    const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
    Object.entries(attrs).forEach(([key, value]) => {
        el.setAttribute(key, String(value));
    });
    return el;
}

function drawScoreChart(history) {
    if (!scoreChartSvg || !scoreChartEmpty) {
        return;
    }

    scoreChartSvg.innerHTML = "";

    if (history.length < 2) {
        scoreChartEmpty.hidden = false;
        return;
    }

    scoreChartEmpty.hidden = true;

    const width = 100;
    const height = 100;
    const left = 8;
    const right = 96;
    const top = 8;
    const bottom = 92;
    const chartWidth = right - left;
    const chartHeight = bottom - top;

    const minScore = 0;
    const maxScore = 100;

    // Grid lines for easier readability.
    [0, 25, 50, 75, 100].forEach((score) => {
        const y = top + chartHeight - (score - minScore) * chartHeight / (maxScore - minScore);
        const grid = createSvgEl("line", {
            x1: left,
            y1: y,
            x2: right,
            y2: y,
            stroke: "#e0e3e8",
            "stroke-width": 0.4,
        });
        scoreChartSvg.appendChild(grid);
    });

    const points = history.map((item, idx) => {
        const x = left + (idx * chartWidth) / (history.length - 1);
        const boundedScore = Math.max(minScore, Math.min(maxScore, item.score));
        const y = top + chartHeight - (boundedScore - minScore) * chartHeight / (maxScore - minScore);
        return { x, y, score: boundedScore, label: item.date_label || "" };
    });

    const polylinePoints = points.map((p) => `${p.x},${p.y}`).join(" ");
    const trendLine = createSvgEl("polyline", {
        points: polylinePoints,
        fill: "none",
        stroke: "#2f343b",
        "stroke-width": 1.2,
    });
    scoreChartSvg.appendChild(trendLine);

    points.forEach((point) => {
        const dot = createSvgEl("circle", {
            cx: point.x,
            cy: point.y,
            r: 1.1,
            fill: "#1f2329",
        });
        const title = createSvgEl("title", {});
        title.textContent = `${point.label}: ${point.score}`;
        dot.appendChild(title);
        scoreChartSvg.appendChild(dot);
    });
}

drawScoreChart(parseScoreHistory());
