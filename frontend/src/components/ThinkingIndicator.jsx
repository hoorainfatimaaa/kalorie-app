import { useState, useEffect, useMemo } from "react";
import "./ThinkingIndicator.css";

const THINKING_WORDS = [
    "Digesting",
    "Crunching numbers",
    "Counting macros",
    "Counting carbs",
    "Weighing options",
    "Weighing it up",
    "Measuring portions",
    "Sizing up portions",
    "Portioning",
    "Chewing it over",
    "Balancing the plate",
    "Balancing macros",
    "Checking labels",
    "Reading the label",
    "Tallying nutrients",
    "Cross-checking nutrients",
    "Calculating calories",
    "Adding it up",
    "Doing the sums",
    "Simmering",
    "Marinating",
    "Steeping",
    "Brewing",
    "Prepping",
    "Blending ideas",
    "Whisking",
    "Folding it in",
    "Stirring",
    "Sifting",
    "Seasoning",
    "Zesting",
    "Plating up",
    "Garnishing",
    "Drizzling",
    "Slicing",
    "Dicing",
    "Taste-testing",
    "Sampling",
    "Trimming the fat",
    "Topping up protein",
    "Rounding out the meal",
    "Filling the plate",
    "Logging it"
];

const VOICE_THINKING_WORDS = [
    "Listening back",
    "Transcribing",
    "Catching that",
    "Tuning in",
    "Replaying",
    "Picking that up",
    "Making it out"
];

const MIN_MS = 1000;
const MAX_MS = 2000;

function shuffled(list) {
    const copy = [...list];
    for (let i = copy.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [copy[i], copy[j]] = [copy[j], copy[i]];
    }
    return copy;
}

function ThinkingIndicator({ words = THINKING_WORDS, minInterval = MIN_MS, maxInterval = MAX_MS }) {

    const order = useMemo(() => shuffled(words), [words]);
const [index, setIndex] = useState(0);

    useEffect(() => {
        if (order.length < 2) return;

        let timer;

        const tick = () => {
            const delay = minInterval + Math.random() * (maxInterval - minInterval);
            timer = setTimeout(() => {
                setIndex((i) => (i + 1) % order.length);
                tick();
            }, delay);
        };

        tick();
        return () => clearTimeout(timer);
    }, [order, minInterval, maxInterval]);

    const word = order[index % order.length];

    return (
        <div className="thinking-text">
            <span key={word} className="thinking-word">
                {word}
                <span className="thinking-dots" aria-hidden="true">
                    <i></i><i></i><i></i>
                </span>
            </span>
        </div>
    );
}

export { THINKING_WORDS, VOICE_THINKING_WORDS };
export default ThinkingIndicator;