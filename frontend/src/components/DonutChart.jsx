import "./DonutChart.css";

function DonutChart({ percent, size, strokeWidth, color, centerValue, centerLabel, glow, valueFontSize }) {

    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (percent / 100) * circumference;

    return (

        <div className={`donut-wrapper ${glow ? "donut-glow" : ""}`} style={{ width: size, height: size }}>

            <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>

                <circle
                    className="donut-track"
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    strokeWidth={strokeWidth}
                    fill="none"
                />

                <circle
                    className="donut-fill"
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    strokeWidth={strokeWidth}
                    fill="none"
                    stroke={color}
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                    strokeLinecap="round"
                    transform={`rotate(-90 ${size / 2} ${size / 2})`}
                />

            </svg>

            <div className="donut-center">
                <span
                    className="donut-value"
                    style={valueFontSize ? { fontSize: valueFontSize } : undefined}
                >
                    {centerValue}
                </span>
                {centerLabel && <span className="donut-label">{centerLabel}</span>}
            </div>

        </div>

    );

}

export default DonutChart;
