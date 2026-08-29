import { useState, useEffect, useRef } from "react";
import Navbar from "../components/Navbar";
import "./Aiassistant.css";
import { FiMic, FiChevronDown, FiPlus, FiArrowUp } from "react-icons/fi";
import { API_URL } from "../config";

const GREETING_MESSAGE = {
    sender: "ai",
    text: "Hello! I'm your personal nutrition assistant. How can I help you today?"
};
import DonutChart from "../components/DonutChart";
import ThinkingIndicator, { VOICE_THINKING_WORDS } from "../components/ThinkingIndicator";

const MEAL_TYPE_ICONS = {
    breakfast: "🌅",
    lunch: "🥗",
    dinner: "🌙",
    snack: "🍎"
};

const DISPLAY_SKELETON_INTENTS = new Set([
    "show_profile",
    "show_progress",
    "show_meal_history"
]);

const PROFILE_SKELETON_ROWS = [
    "Full Name", "Age", "Gender", "Height", "Weight",
    "Activity Level", "Fitness Goal", "Country", "Region"
];

function DisplaySkeleton({ intent }) {

    if (intent === "show_profile") {
        return (
            <div className="ai-card profile-snapshot-card">
                <div className="ai-card-header">
                    <span className="ai-card-icon">👤</span>
                    <span>Profile Snapshot</span>
                </div>
                <div className="ai-stat-grid">
                    {PROFILE_SKELETON_ROWS.map(label => (
                        <div className="ai-stat-box" key={label}>
                            <span className="ai-stat-label">{label}</span>
                            <span className="ai-stat-value meal-field-pending">Loading...</span>
                        </div>
                    ))}
                </div>
                <div className="profile-tags-row">
                    <span className="profile-tag meal-field-pending">Loading...</span>
                    <span className="profile-tag warn meal-field-pending">Loading...</span>
                    <span className="profile-tag meal-field-pending">Loading...</span>
                </div>
            </div>
        );
    }

    if (intent === "show_progress") {
        return (
            <div className="ai-card chat-progress-card">
                <div className="ai-card-header">
                    <span className="ai-card-icon">📊</span>
                    <span>Today's Progress</span>
                </div>
                <div className="chat-progress-main">
                    <DonutChart
                        percent={0}
                        size={90}
                        strokeWidth={8}
                        color="#D8DCD9"
                        centerValue="--"
                        centerLabel="loading"
                    />
                    <div className="chat-progress-remaining">
                        <strong className="meal-field-pending">--</strong>
                        <span>Remaining Today</span>
                    </div>
                </div>
                <div className="chat-progress-macros">
                    {["Protein", "Carbs", "Fat"].map(name => (
                        <div className="chat-progress-macro" key={name}>
                            <DonutChart
                                percent={0}
                                size={54}
                                strokeWidth={5}
                                color="#D8DCD9"
                                centerValue="--"
                                valueFontSize="12px"
                            />
                            <span>{name}</span>
                            <small className="meal-field-pending">--</small>
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    if (intent === "show_meal_history") {
        return (
            <div className="ai-card meal-history-chat-card">
                <div className="diet-plan-card-header">
                    <div className="ai-card-header">
                        <span className="ai-card-icon">🍽️</span>
                        <span>Meal History</span>
                    </div>
                </div>
                <div className="diet-plan-subtitle meal-field-pending">
                    Loading your meals...
                </div>
                <div className="ai-stat-grid">
                    {[0, 1, 2, 3].map(i => (
                        <div className="ai-stat-box" key={i}>
                            <span className="ai-stat-label meal-field-pending">Loading...</span>
                            <span className="ai-stat-value meal-field-pending">--</span>
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    return null;
}


function mealTypeIcon(type) {
    return MEAL_TYPE_ICONS[(type || "").toLowerCase()] || "🍽️";
}

const CONFLICT_ALERT_TITLES = {
    allergy: "Allergy Alert",
    dietary_preference: "Dietary Preference Alert",
    medical_condition: "Medical Condition Alert"
};


function getSpokenText(msg) {

    let base;

    if (msg.intent === "show_profile" && msg.data) {
        const p = msg.data;
        base = `Here is your profile. Age ${p.age || "not set"}. `
            + `Gender ${p.gender || "not set"}. `
            + `Height ${p.height || "not set"} centimeters. `
            + `Weight ${p.weight || "not set"} kilograms. `
            + `Activity level ${(p.activity_level || "not set").replaceAll("_", " ")}. `
            + `Fitness goal ${(p.fitness_goal || "not set").replaceAll("_", " ")}. `
            + `Dietary preference: ${p.dietary_preferences || "none set"}. `
            + `Allergies: ${p.allergies || "none on file"}. `
            + `Medical condition: ${p.medical_condition || "none on file"}. `
            + `Country: ${p.country || "not set"}. `
            + `Region: ${p.region || "not set"}.`;

    } else if (msg.intent === "show_progress" && msg.data) {
        const d = msg.data;
        base = `Today's progress. You've had ${Math.round(d.calories_consumed)} of `
            + `${Math.round(d.calorie_goal)} calories, ${Math.round(d.calories_remaining)} remaining. `
            + `Protein: ${Math.round(d.protein_consumed)} of ${Math.round(d.protein_goal)} grams. `
            + `Carbs: ${Math.round(d.carbs_consumed)} of ${Math.round(d.carbs_goal)} grams. `
            + `Fat: ${Math.round(d.fat_consumed)} of ${Math.round(d.fat_goal)} grams.`;

    } else if (msg.intent === "calorie_status" && msg.data) {
        const d = msg.data;
        base = d.exceeded
            ? `You've exceeded your calorie goal by ${Math.round(d.exceeded_by)} calories.`
            : `You're on track. ${Math.round(d.calories_remaining)} calories remaining today.`;

    } else if (msg.intent === "show_meal_history" && msg.data) {
        const meals = msg.data.meals || [];
        if (meals.length === 0) {
            base = "You haven't logged any meals yet.";
        } else {
            const summary = meals
                .slice(0, 5)
                .map(m => `${m.meal_name}, ${Math.round(m.calories)} calories`)
                .join(". ");
            base = `Here are your recent meals. ${summary}.`;
        }

    } else if (msg.intent === "show_memories" && msg.data) {
        const memories = msg.data.memories || [];
        if (memories.length === 0) {
            base = "I don't have any long-term preferences or habits saved for you yet.";
        } else {
            const summary = memories
                .slice(0, 5)
                .map(m => `${m.memory_key.replaceAll(/[_:]/g, " ")}: ${m.memory_value.replaceAll("_", " ")}`)
                .join(". ");
            base = `Here's what I remember about you. ${summary}.`;
        }

    } else if (
        msg.intent === "update_profile" &&
        msg.updates &&
        Object.keys(msg.updates).length > 0
    ) {
        const changedSummary = Object.entries(msg.updates)
            .map(([field, value]) => `${field.replaceAll("_", " ")}: ${value}`)
            .join(", ");

        base = msg.calorieGoal != null
            ? `Your profile has been updated. ${changedSummary}. Updated targets: `
                + `${msg.calorieGoal} calories, ${msg.proteinGoal} grams protein, `
                + `${msg.carbsGoal} grams carbs, ${msg.fatGoal} grams fat.`
            : `Your profile has been updated. ${changedSummary}.`;

    } else {
        base = typeof msg.text === "object" ? msg.text.reply : msg.text;
    }

    if (msg.guidance) {
        base = `${base} ${msg.guidance.replaceAll("\n\n", " ")}`;
    }

    if (msg.planAdjustment?.message) {
        base = `${base} ${msg.planAdjustment.message}`;
    }

    return base;
}

function Aiassistant() {

    const [message, setMessage] = useState("");
    const [selectedImage, setSelectedImage] = useState(null);
    const [imageName, setImageName] = useState("");
    const [messages, setMessages] = useState([]);
    const [isTyping, setIsTyping] = useState(false);
    const chatEndRef = useRef(null);
    const [isRecording, setIsRecording] = useState(false);
    const [isProcessingAudio, setIsProcessingAudio] = useState(false);
    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);
    const [audioPreview, setAudioPreview] = useState(null);
    const [speakingIndex, setSpeakingIndex] = useState(null);
    const currentAudioRef = useRef(null);
    const speakRequestRef = useRef(0);
    const [recordingTime, setRecordingTime] = useState(0);
    const timerRef = useRef(null);
    const [expandedDay, setExpandedDay] = useState(null);
    const [expandedMeal, setExpandedMeal] = useState({});
    const [deleteTarget, setDeleteTarget] = useState(null);
    const [nutritionAlert, setNutritionAlert] = useState(null);
    const [conflictAlert, setConflictAlert] = useState(null);
    const [planAdjustmentAlert, setPlanAdjustmentAlert] = useState(null);
    const [dailyReminder, setDailyReminder] = useState(null);
    useEffect(() => {

    if (chatEndRef.current) {

        chatEndRef.current.scrollIntoView({
            behavior: "smooth"
        });

    }

}, [messages, isTyping]);
    useEffect(() => {

    const loadChatHistory = async () => {

        try {

            const token = localStorage.getItem("token");

            const response = await fetch(`${API_URL}/chat/history`, {
                method: "GET",
                headers: {
                    Authorization: `Bearer ${token}`
                }
            });
            if (!response.ok) {
    console.error("Failed to load history");
    return;
}

const payload = await response.json();
const data = payload.history || [];

if (payload.reminder) {
    setDailyReminder(payload.reminder);
}

if (data.length === 0) {

    setMessages([GREETING_MESSAGE]);

}
else {

    setMessages(
        [GREETING_MESSAGE].concat(data.map(msg => ({
            sender: msg.sender,
            text: msg.text || msg.message,
            intent: msg.intent || null,
            plan: msg.plan || null,
            portion: msg.portion || null,
            isEstimated: msg.is_estimated ?? null,
            image: msg.image || null,
            audio: msg.audio || null,
            data: msg.data || null,
            updates: msg.updates || null,
            profile: msg.profile || null,
            calorieGoal: msg.calorie_goal ?? null,
            proteinGoal: msg.protein_goal ?? null,
            carbsGoal: msg.carbs_goal ?? null,
            fatGoal: msg.fat_goal ?? null,
            guidance: msg.guidance || null,
            deletedScope: msg.deleted_scope || null,
            planAdjustment: msg.plan_adjustment || null,
            pendingMealType: msg.pending_meal_type || null,
            additionalData: msg.additional_data || null
        })))
    );

}

        } catch (error) {

            console.error("Failed to load chat history:", error);

        }

    };

    loadChatHistory();

}, []);
    const removeImage = () => {
        setSelectedImage(null);
        setImageName("");

        const fileInput = document.getElementById("imageUpload");
        if (fileInput) {
            fileInput.value = "";
        }
    };

    const requestDeleteMeal = (messageIndex, meal, additionalIndex = null) => {
        setDeleteTarget({ messageIndex, additionalIndex, mealId: meal.id, mealName: meal.meal_name });
    };

    const cancelDeleteMeal = () => {
        setDeleteTarget(null);
    };

    const confirmDeleteMeal = async () => {

        if (!deleteTarget) return;

        const { messageIndex, additionalIndex, mealId } = deleteTarget;

        try {

            const token = localStorage.getItem("token");

            const response = await fetch(`${API_URL}/meals/${mealId}`, {
                method: "DELETE",
                headers: {
                    Authorization: `Bearer ${token}`
                }
            });

            if (response.ok) {

                setMessages(prev => prev.map((m, i) => {

                    if (i !== messageIndex) return m;

                    if (additionalIndex == null) {
                        if (!m.data?.meals) return m;
                        return {
                            ...m,
                            data: {
                                ...m.data,
                                meals: m.data.meals.filter(meal => meal.id !== mealId)
                            }
                        };
                    }

                    if (!m.additionalData) return m;
                    return {
                        ...m,
                        additionalData: m.additionalData.map((item, idx) => {
                            if (idx !== additionalIndex || !item.data?.meals) return item;
                            return {
                                ...item,
                                data: {
                                    ...item.data,
                                    meals: item.data.meals.filter(meal => meal.id !== mealId)
                                }
                            };
                        })
                    };

                }));

            } else {

                const data = await response.json();
                alert(data.message || "Failed to delete meal.");

            }

        } catch (error) {

            console.error(error);
            alert("Unable to connect to the server.");

        } finally {

            setDeleteTarget(null);

        }

    };

    const sendMessage = async () => {

        if (message.trim() === "" && !selectedImage) return;

        const currentMessage = message;
        const currentImage = selectedImage;

   
        if (currentMessage.trim() !== "") {

            setMessages(prev => [
                ...prev,
                {
                    sender: "user",
                    text: currentMessage
                }
            ]);

        }

        if (currentImage) {

            setMessages(prev => [
                ...prev,
                {
                    sender: "user",
                    image: URL.createObjectURL(currentImage)//creates url for image so that image is displayed even before it reaches flask
                                }
            ]);

        }
        setMessage("");
        setSelectedImage(null);
        setImageName("");

        const fileInput = document.getElementById("imageUpload");
        if (fileInput) {
            fileInput.value = "";
        }
        setIsTyping(true);

        try {

            const token = localStorage.getItem("token");

            const formData = new FormData();

            formData.append("message", currentMessage);

            if (currentImage) {
                formData.append("image", currentImage);
            }

            const response = await fetch(
                `${API_URL}/chat/stream`,
                {
                    method: "POST",

                    headers: {
                        Authorization: `Bearer ${token}`
                    },

                    body: formData
                }
            );

            if (!response.ok || !response.body) {

                let serverMessage = "Something went wrong.";

                try {
                    const failed = await response.json();
                    serverMessage = failed.message || serverMessage;
                }
                catch {
               
                }

                setMessages(prev => [
                    ...prev,
                    {
                        sender: "ai",
                        text: serverMessage
                    }
                ]);
                setIsTyping(false);
                return;
            }


            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            let sseBuffer = "";
            let streamedText = "";
            let placeholderAdded = false;
            let streamError = null;
            let data = null;
            let mealDraft = null;

            const startPlaceholder = () => {
                if (placeholderAdded) return;
                placeholderAdded = true;
                setIsTyping(false);
                setMessages(prev => [
                    ...prev,
                    { sender: "ai", text: "", streaming: true }
                ]);
            };

            const paintDraft = (draft) => {
                setMessages(prev => {
                    const next = [...prev];
                    next[next.length - 1] = {
                        ...next[next.length - 1],
                        mealDraft: draft
                    };
                    return next;
                });
            };


            const MEAL_FIELD_MS = 110;

            let mealQueue = [];
            let mealDraining = false;
            let mealDrained = null;

            const drainMealQueue = () => {
                if (mealQueue.length === 0) {
                    mealDraining = false;
                    if (mealDrained) {
                        mealDrained();
                        mealDrained = null;
                    }
                    return;
                }

                const { field, value } = mealQueue.shift();
                mealDraft = { ...mealDraft, [field]: value };
                paintDraft(mealDraft);

                setTimeout(drainMealQueue, MEAL_FIELD_MS);
            };

            const queueMealField = (field, value) => {
                mealQueue.push({ field, value });
                if (!mealDraining) {
                    mealDraining = true;
                    setTimeout(drainMealQueue, MEAL_FIELD_MS);
                }
            };
            const mealQueueSettled = () => (
                !mealDraining && mealQueue.length === 0
                    ? Promise.resolve()
                    : new Promise(resolve => { mealDrained = resolve; })
            );

            const paintStreamedText = (text) => {
                setMessages(prev => {
                    const next = [...prev];
                    next[next.length - 1] = {
                        ...next[next.length - 1],
                        text
                    };
                    return next;
                });
            };

            while (true) {

                const { done, value } = await reader.read();

                if (done) {
                    break;
                }

                sseBuffer += decoder.decode(value, { stream: true });

                const frames = sseBuffer.split("\n\n");
                sseBuffer = frames.pop();

                for (const frame of frames) {

                    const nameMatch = frame.match(/^event: (.*)$/m);
                    const dataMatch = frame.match(/^data: (.*)$/m);

                    if (!nameMatch || !dataMatch) {
                        continue;
                    }

                    let payload;

                    try {
                        payload = JSON.parse(dataMatch[1]);
                    }
                    catch {
                        continue;
                    }

                    if (nameMatch[1] === "delta") {

                        startPlaceholder();

                        streamedText += payload.text;
                        paintStreamedText(streamedText);
                    }

                    else if (nameMatch[1] === "reset") {
                     
                        streamedText = "";
                        paintStreamedText("");
                    }

                    else if (nameMatch[1] === "intent") {
                        startPlaceholder();
                        setMessages(prev => {
                            const next = [...prev];
                            next[next.length - 1] = {
                                ...next[next.length - 1],
                                streamIntent: payload.intent
                            };
                            return next;
                        });
                    }

                    else if (nameMatch[1] === "meal_start") {
                        startPlaceholder();
                        mealDraft = { intent: payload.intent };
                        paintDraft(mealDraft);
                    }

                    else if (nameMatch[1] === "meal_cancel") {
                       
                        mealQueue = [];
                        mealDraft = null;
                        if (placeholderAdded) {
                            setMessages(prev => prev.slice(0, -1));
                            placeholderAdded = false;
                        }
                        setIsTyping(true);
                    }

                    else if (nameMatch[1] === "meal_field") {
                        if (mealDraft) {
                            queueMealField(payload.field, payload.value);
                        }
                    }

                    else if (nameMatch[1] === "done") {
                        data = payload;
                    }

                    else if (nameMatch[1] === "error") {
                        streamError = payload.message || "Something went wrong.";
                    }
                }
            }

            if (!data) {

                const failureText = streamError || "The connection was interrupted.";

                setMessages(prev => {
                    const next = [...prev];
                    const failed = { sender: "ai", text: failureText };

                    if (placeholderAdded) {
                        next[next.length - 1] = failed;
                    }
                    else {
                        next.push(failed);
                    }

                    return next;
                });

                setIsTyping(false);
                return;
            }

await mealQueueSettled();

if (data.success && data.reply?.intent === "update_profile") {
    window.dispatchEvent(new Event("profileUpdated"));
}

let aiText = data.reply.reply;

if (data.reply.intent === "diet_plan_confirmation" && data.reply.plan) {

    aiText = data.reply.plan.map(day => {

        let text = `📅 ${day.day}\n\n`;

        day.meals.forEach(meal => {

            text += `
🍽️ ${meal.meal_type}

${meal.meal_name}

${meal.description}

🔥 Calories: ${meal.calories}
💪 Protein: ${meal.protein}g
🍞 Carbs: ${meal.carbs}g
🥑 Fat: ${meal.fat}g

`;

        });

        return text;

    }).join("\n-----------------\n");

}

if (data.reply.intent === "diet_plan_confirmation") {

    aiText = data.reply.reply;

}


setMessages(prev => {

    const next = [...prev];

    const finalMessage = {
        sender: "ai",
        text: aiText,
        intent: data.reply.intent,
        plan: data.reply.plan || null,
        portion: data.reply.portion || null,
        isEstimated: data.reply.is_estimated ?? null,
        data: data.reply.data || null,
        updates: data.reply.updates || null,
        profile: data.reply.profile || null,
        calorieGoal: data.reply.calorie_goal ?? null,
        proteinGoal: data.reply.protein_goal ?? null,
        carbsGoal: data.reply.carbs_goal ?? null,
        fatGoal: data.reply.fat_goal ?? null,
        guidance: data.reply.guidance || null,
        deletedScope: data.reply.deleted_scope || null,
        planAdjustment: data.reply.plan_adjustment || null,
        pendingMealType: data.reply.pending_meal_type || null,
        additionalData: data.reply.additional_data || null
    };


    if (placeholderAdded) {
        next[next.length - 1] = finalMessage;
    }
    else {
        next.push(finalMessage);
    }

    return next;
});

if (data.reply.nutrition_alert && data.reply.nutrition_alert.length > 0) {
    setNutritionAlert({
        items: data.reply.nutrition_alert,
        guidance: data.reply.guidance || ""
    });
}

if (data.reply.conflict_alert) {
    setConflictAlert(data.reply.conflict_alert);
}

if (data.reply.plan_adjustment) {
    setPlanAdjustmentAlert(data.reply.plan_adjustment);
}


setIsTyping(false);
        }

        catch (error) {
           console.error(error);

            setMessages(prev => [
                ...prev,
                {
                    sender: "ai",
                    text: "Unable to connect to the server."
                }
            ]);
            setIsTyping(false);

        }

    };
    const startRecording = async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: true,
    });//request permission to use microphone

    const mediaRecorder = new MediaRecorder(stream);

    mediaRecorderRef.current = mediaRecorder;
    audioChunksRef.current = [];

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunksRef.current.push(event.data);//stores every piece of recorded audio
      }
    };

    mediaRecorder.start();

setIsRecording(true);
setRecordingTime(0);

timerRef.current = setInterval(() => {
    setRecordingTime(prev => prev + 1);
}, 1000);
  } catch (error) {
    console.error("Microphone access denied:", error);
  }
};


const stopRecording = () => {
    const recorder = mediaRecorderRef.current;

    if (!recorder) return;

    recorder.onstop = async () => {

        const audioBlob = new Blob(audioChunksRef.current, {//combines all chunks
            type: "audio/webm",
        });

        const formData = new FormData();
        formData.append("audio", audioBlob, "recording.webm");
        const localAudio = URL.createObjectURL(audioBlob);

    setMessages(prev => [
        ...prev,
        {
            sender: "user",
            audio: localAudio,
            duration: `${recordingTime}s`
        }
    ]);

    setIsTyping(true);

        const token = localStorage.getItem("token");

        try {

            const response = await fetch(
                `${API_URL}/chat/audio`,
                {
                    method: "POST",
                    headers: {
                        Authorization: `Bearer ${token}`
                    },
                    body: formData
                }
            );


            const data = await response.json();

            if (data.success && data.reply?.intent === "update_profile") {
            window.dispatchEvent(new Event("profileUpdated"));
}
            
let aiText = data.reply.reply;
setIsTyping(false);
setMessages(prev => [
    ...prev,
    {
        sender: "ai",
        text: aiText,
        intent: data.reply.intent,
        plan: data.reply.plan || null,
        portion: data.reply.portion || null,
        isEstimated: data.reply.is_estimated ?? null,
        data: data.reply.data || null,
        updates: data.reply.updates || null,
        profile: data.reply.profile || null,
        calorieGoal: data.reply.calorie_goal ?? null,
        proteinGoal: data.reply.protein_goal ?? null,
        carbsGoal: data.reply.carbs_goal ?? null,
        fatGoal: data.reply.fat_goal ?? null,
        guidance: data.reply.guidance || null,
        deletedScope: data.reply.deleted_scope || null,
        planAdjustment: data.reply.plan_adjustment || null,
        pendingMealType: data.reply.pending_meal_type || null,
        additionalData: data.reply.additional_data || null
    }
]);

if (data.reply.nutrition_alert && data.reply.nutrition_alert.length > 0) {
    setNutritionAlert({
        items: data.reply.nutrition_alert,
        guidance: data.reply.guidance || ""
    });
}

if (data.reply.conflict_alert) {
    setConflictAlert(data.reply.conflict_alert);
}

if (data.reply.plan_adjustment) {
    setPlanAdjustmentAlert(data.reply.plan_adjustment);
}


if (data.audio) {

    const audio = new Audio(
        `${API_URL}/uploads/${data.audio}`
    );

    audio.play();

}

        } 
        catch(error){

    console.error("Failed to upload audio:", error);

    setIsTyping(false);

    setMessages(prev=>[
        ...prev,
        {
            sender:"ai",
            text:"Unable to process your voice message."
        }
    ]);

}

    };

    recorder.stop();

setIsRecording(false);

clearInterval(timerRef.current);
};


useEffect(() => {
    return () => {
        speakRequestRef.current += 1;
        if(currentAudioRef.current){
            currentAudioRef.current.pause();
            currentAudioRef.current = null;
        }
    };
}, []);


const stopSpeaking = ()=>{

   
    speakRequestRef.current += 1;

    const playing = currentAudioRef.current;

    if(playing){
        playing.pause();
        playing.currentTime = 0;
        currentAudioRef.current = null;
    }

    setSpeakingIndex(null);

};


const speakText = async(text, index)=>{


    if(speakingIndex === index){
        stopSpeaking();
        return;
    }
    stopSpeaking();

    const requestId = ++speakRequestRef.current;

    setSpeakingIndex(index);

    try{

        const token = localStorage.getItem("token");


        const response = await fetch(
        `${API_URL}/chat/speak`,
        {
            method:"POST",

            headers:{
                "Content-Type":"application/json",
                Authorization:`Bearer ${token}`
            },

            body:JSON.stringify({
                text:text
            })
        });


        const data = await response.json();


     
        if(speakRequestRef.current !== requestId){
            return;
        }

        if(data.audio_base64){

            const audio = new Audio(
            `data:audio/mpeg;base64,${data.audio_base64}`
            );

            currentAudioRef.current = audio;

            audio.onended = ()=>{
                if(speakRequestRef.current === requestId){
                    currentAudioRef.current = null;
                    setSpeakingIndex(null);
                }
            };

            audio.onerror = ()=>{
                if(speakRequestRef.current === requestId){
                    currentAudioRef.current = null;
                    setSpeakingIndex(null);
                }
            };

            audio.play();

        }else{

            setSpeakingIndex(null);

        }


    }catch(error){

        console.error(
        "Audio generation failed:",
        error
        );

        if(speakRequestRef.current === requestId){
            setSpeakingIndex(null);
        }

    }

};

function renderDisplayCard(intent, data, msgIndex, additionalIndex, requestDeleteMeal) {

    if (intent === "show_profile" && data) {

        const p = data;

        const rows = [
            ["Full Name", p.full_name],
            ["Age", p.age ? `${p.age} yrs` : null],
            ["Gender", p.gender],
            ["Height", p.height ? `${p.height} cm` : null],
            ["Weight", p.weight ? `${p.weight} kg` : null],
            ["Activity Level", p.activity_level ? p.activity_level.replaceAll("_", " ") : null],
            ["Fitness Goal", p.fitness_goal ? p.fitness_goal.replaceAll("_", " ") : null],
            ["Country", p.country],
            ["Region", p.region]
        ];

        return (

            <div className="ai-card profile-snapshot-card">

                <div className="ai-card-header">
                    <span className="ai-card-icon">👤</span>
                    <span>Profile Snapshot</span>
                </div>

                <div className="ai-stat-grid">
                    {rows.map(([label, value]) => (
                        <div className="ai-stat-box" key={label}>
                            <span className="ai-stat-label">{label}</span>
                            <span className="ai-stat-value">{value || "Not set"}</span>
                        </div>
                    ))}
                </div>

                <div className="profile-tags-row">
                    <span className="profile-tag">
                        🥗 {p.dietary_preferences || "No dietary preference set"}
                    </span>
                    <span className="profile-tag warn">
                        ⚠️ {p.allergies || "No allergies on file"}
                    </span>
                    <span className="profile-tag">
                        🩺 {p.medical_condition || "No medical condition on file"}
                    </span>
                </div>

            </div>

        );

    }

    if (intent === "show_progress" && data) {

        const d = data;

        const caloriePercent = Math.min((d.calories_consumed / (d.calorie_goal || 1)) * 100, 100);
        const proteinPercent = Math.min((d.protein_consumed / (d.protein_goal || 1)) * 100, 100);
        const carbsPercent = Math.min((d.carbs_consumed / (d.carbs_goal || 1)) * 100, 100);
        const fatPercent = Math.min((d.fat_consumed / (d.fat_goal || 1)) * 100, 100);
        const isOverLimit = d.calorie_goal > 0 && d.calories_consumed > d.calorie_goal;
        const isProteinOver = d.protein_goal > 0 && d.protein_consumed > d.protein_goal;
        const isCarbsOver = d.carbs_goal > 0 && d.carbs_consumed > d.carbs_goal;
        const isFatOver = d.fat_goal > 0 && d.fat_consumed > d.fat_goal;

        return (

            <div className="ai-card chat-progress-card">

                <div className="ai-card-header">
                    <span className="ai-card-icon">📊</span>
                    <span>Today's Progress</span>
                </div>

                <div className="chat-progress-main">

                    <DonutChart
                        percent={caloriePercent}
                        size={90}
                        strokeWidth={8}
                        color={isOverLimit ? "#D9534F" : "#7BAE7F"}
                        centerValue={`${Math.round(d.calories_consumed)}`}
                        centerLabel={`/ ${Math.round(d.calorie_goal)} kcal`}
                        glow={isOverLimit}
                    />

                    <div className="chat-progress-remaining">
                        <strong>{Math.round(d.calories_remaining)} kcal</strong>
                        <span>Remaining Today</span>
                    </div>

                </div>

                <div className="chat-progress-macros">

                    <div className="chat-progress-macro">
                        <DonutChart percent={proteinPercent} size={54} strokeWidth={5} color={isProteinOver ? "#D9534F" : "#4F8F8B"} centerValue={`${Math.round(d.protein_consumed)}g`} valueFontSize="12px" glow={isProteinOver} />
                        <span>Protein</span>
                        <small>{Math.round(d.protein_consumed)}/{Math.round(d.protein_goal)}g</small>
                    </div>

                    <div className="chat-progress-macro">
                        <DonutChart percent={carbsPercent} size={54} strokeWidth={5} color={isCarbsOver ? "#D9534F" : "#E4B363"} centerValue={`${Math.round(d.carbs_consumed)}g`} valueFontSize="12px" glow={isCarbsOver} />
                        <span>Carbs</span>
                        <small>{Math.round(d.carbs_consumed)}/{Math.round(d.carbs_goal)}g</small>
                    </div>

                    <div className="chat-progress-macro">
                        <DonutChart percent={fatPercent} size={54} strokeWidth={5} color={isFatOver ? "#D9534F" : "#D97D82"} centerValue={`${Math.round(d.fat_consumed)}g`} valueFontSize="12px" glow={isFatOver} />
                        <span>Fat</span>
                        <small>{Math.round(d.fat_consumed)}/{Math.round(d.fat_goal)}g</small>
                    </div>

                </div>

            </div>

        );

    }

    if (intent === "calorie_status" && data) {

        const d = data;
        const percent = Math.min((d.calories_consumed / (d.calorie_goal || 1)) * 100, 100);

        return (

            <div className="ai-card calorie-status-card">

                <div className="ai-card-header">
                    <span className="ai-card-icon">🔥</span>
                    <span>Calorie Status</span>
                </div>

                <div className="chat-progress-main">
                    <DonutChart
                        percent={percent}
                        size={90}
                        strokeWidth={8}
                        color={d.exceeded ? "#D9534F" : "#7BAE7F"}
                        centerValue={`${Math.round(d.calories_consumed)}`}
                        centerLabel={`/ ${Math.round(d.calorie_goal)} kcal`}
                        glow={d.exceeded}
                    />
                </div>

                <div className={`calorie-status-banner ${d.exceeded ? "over" : "ok"}`}>
                    {d.exceeded
                        ? `⚠️ Exceeded by ${Math.round(d.exceeded_by)} kcal`
                        : `On track — ${Math.round(d.calories_remaining)} kcal remaining`}
                </div>

            </div>

        );

    }

    if (intent === "show_meal_history" && data) {

        const meals = data.meals || [];

        const dateGroups = [];
        meals.forEach((meal) => {
            const dateLabel = meal.created_at
                ? new Date(meal.created_at).toLocaleDateString([], {
                    weekday: "long",
                    month: "short",
                    day: "numeric"
                })
                : "Unknown date";
            let group = dateGroups.find(g => g.label === dateLabel);
            if (!group) {
                group = { label: dateLabel, meals: [] };
                dateGroups.push(group);
            }
            group.meals.push(meal);
        });

        const totalCalories = meals.reduce((sum, m) => sum + (m.calories || 0), 0);

        return (

            <div className="ai-card meal-history-chat-card">

                <div className="diet-plan-card-header">
                    <div className="ai-card-header">
                        <span className="ai-card-icon">🍽️</span>
                        <span>Meal History</span>
                    </div>
                    {meals.length > 0 && (
                        <span className="diet-plan-badge">{meals.length} meals</span>
                    )}
                </div>

                {meals.length === 0 ? (

                    <div className="ai-empty-state">No meals logged yet.</div>

                ) : (

                    <>

                        <div className="diet-plan-subtitle">
                            {Math.round(totalCalories)} kcal total across {meals.length} meals
                        </div>

                        <div className="meal-history-chat-list">

                            {dateGroups.map((group) => (

                                <div className="meal-history-date-group" key={group.label}>

                                    <div className="meal-history-date-label">{group.label}</div>

                                    {group.meals.map((meal) => (

                                        <div className="meal-history-chat-row" key={meal.id}>

                                            <div className="meal-history-chat-top">
                                                <h4>{meal.meal_name}</h4>
                                                <div className="meal-history-chat-top-right">
                                                    <span className="meal-history-chat-time">
                                                        {meal.created_at
                                                            ? new Date(meal.created_at).toLocaleTimeString([], {
                                                                hour: "2-digit",
                                                                minute: "2-digit"
                                                            })
                                                            : ""}
                                                    </span>
                                                    <button
                                                        className="meal-history-delete-btn"
                                                        title="Delete this meal"
                                                        onClick={() => requestDeleteMeal(msgIndex, meal, additionalIndex)}
                                                    >
                                                        ✕
                                                    </button>
                                                </div>
                                            </div>

                                            {meal.portion && (
                                                <p className="meal-history-chat-portion">{meal.portion}</p>
                                            )}

                                            <div className="meal-history-chat-macros">
                                                <span className="chip cal">🔥 {Math.round(meal.calories)}</span>
                                                <span className="chip protein">💪 {Math.round(meal.protein)}g</span>
                                                <span className="chip carbs">🍞 {Math.round(meal.carbs)}g</span>
                                                <span className="chip fat">🥑 {Math.round(meal.fat)}g</span>
                                            </div>

                                        </div>

                                    ))}

                                </div>

                            ))}

                        </div>

                    </>

                )}

            </div>

        );

    }

    if (intent === "show_memories" && data) {

        const memories = data.memories || [];

        return (

            <div className="ai-card profile-snapshot-card">

                <div className="ai-card-header">
                    <span className="ai-card-icon">🧠</span>
                    <span>What I Remember About You</span>
                </div>

                {memories.length === 0 ? (

                    <div className="ai-empty-state">Nothing saved yet — mention a lasting preference or habit and I'll remember it.</div>

                ) : (

                    <div className="ai-stat-grid">
                        {memories.map((m) => (
                            <div className="ai-stat-box" key={m.id}>
                                <span className="ai-stat-label">{m.memory_key.replaceAll(/[_:]/g, " ")}</span>
                                <span className="ai-stat-value">{m.memory_value.replaceAll("_", " ")}</span>
                            </div>
                        ))}
                    </div>

                )}

            </div>

        );

    }

    return null;

}


   return (

        <>
            <Navbar />
            <div className="assistant-container">


                <div className="assistant-layout">

                    <div className="chat-card">

                        <div className="chat-card-header">

                            <h2>AI Assistant</h2>
                        </div>

                        <div className="chat-container">

                            {messages.map((msg, index) => (

                                <div
                                    key={index}
                                    className={`chat-message ${msg.sender}`}
                                >
                               {(msg.text || msg.mealDraft || msg.streamIntent) && (

<div className="ai-message-content">
{
(() => {

    const text = msg.text;
    const draft = msg.mealDraft;
    if (msg.streaming && !msg.data &&
        DISPLAY_SKELETON_INTENTS.has(msg.streamIntent)) {
        return <DisplaySkeleton intent={msg.streamIntent} />;
    }

    if (msg.streaming && !draft && msg.streamIntent !== "nutrition_question") {
        return <p className="ai-plain-reply ai-streaming-reply">{text}</p>;
    }

    // Fields still in flight render as a placeholder rather than blank.
    const orPending = (value, suffix) => (
        value === undefined || value === null
            ? <span className="meal-field-pending">Calculating...</span>
            : `${value}${suffix || ""}`
    );

if (
    draft ||
    ((msg.intent === "meal_log" ||
    msg.intent === "meal_update") &&
    !msg.pendingMealType)
)
    {

        const meal = draft
            ? draft.meal_name
            : text.match(/Meal:\s*([\s\S]*?)Meal Type:/)?.[1]?.trim();

        const mealType = draft
            ? draft.meal_type
            : text.match(/Meal Type:\s*([\s\S]*?)Nutrition:/)?.[1]?.trim();

        const calories = draft
            ? draft.calories
            : text.match(/Calories:\s*(\d+)/)?.[1];

        const protein = draft
            ? draft.protein
            : text.match(/Protein:\s*(\d+)/)?.[1];

        const carbs = draft
            ? draft.carbs
            : text.match(/Carbs:\s*(\d+)/)?.[1];

        const fat = draft
            ? draft.fat
            : text.match(/Fat:\s*(\d+)/)?.[1];

        const portion = draft ? draft.portion : msg.portion;
        const isEstimated = draft ? draft.is_estimated : msg.isEstimated;

        const isUpdate = (draft ? draft.intent : msg.intent) === "meal_update";

        return (

            <div className="ai-card meal-log-card">

                <div className="diet-plan-card-header">
                    <div className="ai-card-header">
                        {isUpdate && <span className="ai-card-icon">🔄</span>}
                        <span>{isUpdate ? "Meal Updated" : "Meal Logged"}</span>
                    </div>
                    {mealType ? (
                        <span className="diet-plan-badge">
                            {mealTypeIcon(mealType)} {mealType}
                        </span>
                    ) : draft ? (
                        <span className="diet-plan-badge meal-field-pending">
                            &nbsp;&nbsp;&nbsp;&nbsp;
                        </span>
                    ) : null}
                </div>

                <div className="meal-name">
                    🍽️ {orPending(meal)}
                </div>

                {portion && (
                    <span className="profile-tag">📏 {portion}</span>
                )}

                <div className="ai-stat-grid">

                    <div className="ai-stat-box">
                        <span className="ai-stat-label">🔥 Calories</span>
                        <span className="ai-stat-value">{orPending(calories)}</span>
                    </div>

                    <div className="ai-stat-box">
                        <span className="ai-stat-label">💪 Protein</span>
                        <span className="ai-stat-value">{orPending(protein, "g")}</span>
                    </div>

                    <div className="ai-stat-box">
                        <span className="ai-stat-label">🍞 Carbs</span>
                        <span className="ai-stat-value">{orPending(carbs, "g")}</span>
                    </div>

                    <div className="ai-stat-box">
                        <span className="ai-stat-label">🥑 Fat</span>
                        <span className="ai-stat-value">{orPending(fat, "g")}</span>
                    </div>

                </div>

                <div className={draft ? "meal-success meal-field-pending" : "meal-success"}>
                    {draft
                        ? (isUpdate ? "Updating..." : "Logging...")
                        : (isUpdate ? "✔ Updated Today's Progress" : "✔ Added to Today's Progress")}
                </div>

                {isEstimated && (

                    <div className="meal-estimated-note">
                        📐 Estimated portion — tell me the exact amount for more accurate tracking.
                    </div>

                )}

                {msg.guidance && (

                    <div className="meal-guidance-note">
                        {msg.guidance.split("\n\n").map((line, i) => (
                            <p key={i}>{line}</p>
                        ))}
                    </div>

                )}

                {msg.planAdjustment && (

                    <div className="plan-adjustment-note">

                        <div className="plan-adjustment-header">
                            📋 Plan Adjusted
                        </div>

                        <p>{msg.planAdjustment.message}</p>

                        {msg.planAdjustment.today?.length > 0 && (
                            <div className="plan-adjustment-group">
                                <h5>Today's updated meals</h5>
                                {msg.planAdjustment.today.map((slot, i) => (
                                    <div className="plan-adjustment-slot" key={i}>
                                        <span className="plan-adjustment-slot-label">
                                            {mealTypeIcon(slot.meal_type)} {slot.meal_type} — {slot.meal_name}
                                        </span>
                                        <span className="plan-adjustment-slot-values">
                                            {slot.original.calories} → {slot.adjusted.calories} kcal
                                        </span>
                                    </div>
                                ))}
                            </div>
                        )}

                        {msg.planAdjustment.week?.length > 0 && (
                            <div className="plan-adjustment-group">
                                <h5>Rest of this week</h5>
                                {msg.planAdjustment.week.map(day => (
                                    <div className="plan-adjustment-day" key={day.day}>
                                        <div className="plan-adjustment-day-label">📅 {day.day}</div>
                                        {day.meals.map((slot, i) => (
                                            <div className="plan-adjustment-slot" key={i}>
                                                <span className="plan-adjustment-slot-label">
                                                    {mealTypeIcon(slot.meal_type)} {slot.meal_type} — {slot.meal_name}
                                                </span>
                                                <span className="plan-adjustment-slot-values">
                                                    {slot.original.calories} → {slot.adjusted.calories} kcal
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                ))}
                            </div>
                        )}

                    </div>

                )}

            </div>

        );


    }
    if (msg.intent === "meal_delete") {

        return (

            <div className="ai-card meal-delete-card">

                <div className="ai-card-header">
                    <span className="ai-card-icon delete">🗑️</span>
                    <span>
                        {msg.deletedScope === "all_today"
                            ? "Today's Meals Cleared"
                            : "Meal Removed"}
                    </span>
                </div>

                <p className="profile-update-note">{text}</p>

            </div>

        );

    }
    if (msg.intent === "delete_diet_plan") {

        return (

            <div className="ai-card meal-delete-card">

                <div className="ai-card-header">
                    <span className="ai-card-icon delete">🗑️</span>
                    <span>Weekly Plan Deleted</span>
                </div>

                <p className="profile-update-note">{text}</p>

            </div>

        );

    }
    if (msg.intent === "delete_profile") {

        return (

            <div className="ai-card meal-delete-card">

                <div className="ai-card-header">
                    <span className="ai-card-icon delete">🗑️</span>
                    <span>Profile Reset</span>
                </div>

                <p className="profile-update-note">{text}</p>

            </div>

        );

    }
    if (
    (msg.intent === "diet_plan_confirmation" ||
        msg.intent === "show_weekly_plan") &&
    (msg.plan || msg.data?.plan)
) {

    const weekPlan = msg.plan || msg.data.plan;
    const viewOnly = msg.intent === "show_weekly_plan";

    return (

        <div className="ai-card diet-plan-card">

            <div className="diet-plan-card-header">
                <div className="ai-card-header">
                    <span className="ai-card-icon">🥗</span>
                    <span>Weekly Meal Plan</span>
                </div>
                <span className="diet-plan-badge">{weekPlan.length}-Day Plan</span>
            </div>

            <div className="diet-plan-subtitle">

                {viewOnly
                    ? "Your saved weekly plan"
                    : "Personalized to your goals and preferences"}

            </div>

            {weekPlan.map((day) => (

                <div
                    key={day.day}
                    className="diet-day"
                >

                    <div
                        className="diet-day-header"
                        onClick={() =>
                            setExpandedDay(
                                expandedDay === day.day
                                    ? null
                                    : day.day
                            )
                        }
                    >

                        <span>

                            📅 {day.day}

                        </span>

                        <FiChevronDown
                            className={`diet-chevron ${expandedDay === day.day ? "open" : ""}`}
                        />

                    </div>

                    {expandedDay === day.day && (

                        <div className="diet-day-content">

                            {day.meals.map((meal, index) => {

                                const mealKey =
                                    `${day.day}-${index}`;

                                return (

                                    <div
                                        key={mealKey}
                                        className="diet-meal"
                                    >

                                        <div
                                            className="diet-meal-header"
                                            onClick={() =>
                                                setExpandedMeal(prev => ({
                                                    ...prev,
                                                    [mealKey]:
                                                        !prev[mealKey]
                                                }))
                                            }
                                        >

                                            <span>

                                                {mealTypeIcon(meal.meal_type)} {meal.meal_type}

                                                {meal.adjusted && (
                                                    <span className="diet-adjusted-tag">Adjusted</span>
                                                )}

                                                {meal.logged && (
                                                    <span className="diet-logged-tag">Logged</span>
                                                )}

                                            </span>

                                            <FiChevronDown
                                                className={`diet-chevron ${expandedMeal[mealKey] ? "open" : ""}`}
                                            />

                                        </div>

                                        {expandedMeal[mealKey] && (

                                            <div className="diet-meal-content">

                                                <h4>

                                                    {meal.meal_name}

                                                </h4>

                                                <p>

                                                    {meal.description}

                                                </p>

                                                {meal.logged ? (

                                                    <>

                                                        <div className="diet-macros-label">
                                                            You were supposed to have: <strong>{meal.meal_name}</strong>
                                                        </div>
                                                        <div className="diet-macros">
                                                            <span className="chip cal">🔥 {meal.calories}</span>
                                                            <span className="chip protein">💪 {meal.protein}g</span>
                                                            <span className="chip carbs">🍞 {meal.carbs}g</span>
                                                            <span className="chip fat">🥑 {meal.fat}g</span>
                                                        </div>

                                                        <div className="diet-macros-label">
                                                            Instead had: <strong>{meal.actual.meal_name}</strong>
                                                        </div>
                                                        <div className="diet-macros">
                                                            <span className="chip cal">🔥 {meal.actual.calories}</span>
                                                            <span className="chip protein">💪 {meal.actual.protein}g</span>
                                                            <span className="chip carbs">🍞 {meal.actual.carbs}g</span>
                                                            <span className="chip fat">🥑 {meal.actual.fat}g</span>
                                                        </div>

                                                    </>

                                                ) : (

                                                    <div className="diet-macros">
                                                        <span className="chip cal">🔥 {meal.calories}</span>
                                                        <span className="chip protein">💪 {meal.protein}g</span>
                                                        <span className="chip carbs">🍞 {meal.carbs}g</span>
                                                        <span className="chip fat">🥑 {meal.fat}g</span>
                                                    </div>

                                                )}

                                            </div>

                                        )}

                                    </div>

                                );

                            })}

                        </div>

                    )}

                </div>

            ))}
            {viewOnly ? (
                <div className="diet-plan-saved-badge">
                    Saved to your profile
                </div>
            ) : (
                <div className="diet-plan-question">
                    Would you like me to save this plan?
                </div>
            )}

        </div>

    );

}
if (msg.intent === "nutrition_question" ||
    msg.streamIntent === "nutrition_question") {

    const parseSource = msg.streaming
        ? text.slice(0, text.lastIndexOf("\n") + 1)
        : text;

    const lines = parseSource
        .split("\n")
        .map(line => line.trim())
        .filter(line => line !== "");

    const stripLead = value => value.replace(/^[\s\-•*–—]+/, "").trim();

    const titleLine = stripLead(lines[0] || "");
    const titleEmoji = titleLine.match(/^(\p{Extended_Pictographic}️?)\s*/u);

    const cardIcon = titleEmoji ? titleEmoji[1] : "🥗";
    const title = titleEmoji
        ? titleLine.slice(titleEmoji[0].length).trim()
        : titleLine;

    const nutrition = [];
    const details = [];
    const tip = [];

    const SECTIONS = {
        "estimated nutrition": "nutrition",
        "nutrition": "nutrition",
        "macros": "nutrition",
        "why": "details",
        "note": "details",
        "notes": "details",
        "details": "details",
        "tip": "tip",
        "tips": "tip"
    };

    const bucketFor = name => (
        name === "nutrition" ? nutrition : name === "tip" ? tip : details
    );

    let section = "details";

    lines.slice(1).forEach(line => {

        const bare = stripLead(line).replace(
            /^(\p{Extended_Pictographic}️?\s*)+/u,
            ""
        );

        if (!bare) return;

        const colonIdx = bare.indexOf(":");

        if (colonIdx > -1) {

            const rawLabel = bare.slice(0, colonIdx).trim();
            const rest = bare.slice(colonIdx + 1).trim();

            const named = SECTIONS[
                rawLabel.replace(/[^\p{L}\s]/gu, "").trim().toLowerCase()
            ];

            if (named) {
                section = named;
                if (rest) bucketFor(named).push(rest);
                return;
            }

            if (
                section === "nutrition" &&
                rest &&
                rawLabel.length <= 22 &&
                rest.length <= 90
            ) {
                nutrition.push({
                    label: rawLabel,
                    value: rest,
                    wide: rest.length > 34
                });
                return;
            }

        }

        if (section === "tip") tip.push(bare);
        else details.push(bare);

    });

    return (

        <div className="ai-card nutrition-card">

            <div className="ai-card-header">
                <span className="ai-card-icon">{cardIcon}</span>
                <span>
                    {title || (msg.streaming
                        ? <span className="meal-field-pending">Preparing answer...</span>
                        : title)}
                </span>
            </div>

            {nutrition.length > 0 && (

                <div className="ai-stat-grid">

                    {nutrition.map((item, i) => (
                        <div
                            className={`ai-stat-box ${item.wide ? "wide" : ""}`}
                            key={i}
                        >
                            <span className="ai-stat-label">{item.label}</span>
                            <span className="ai-stat-value">{item.value}</span>
                        </div>
                    ))}

                </div>

            )}

            {details.length > 0 && (

                <div className="nutrition-section">

                    <ul className="nutrition-list">
                        {details.map((item, i) => (
                            <li key={i}>{item}</li>
                        ))}
                    </ul>

                </div>

            )}

            {tip.length > 0 && (

                <div className="nutrition-tip">
                    <span className="nutrition-tip-label">Tip</span>
                    {tip.map((item, i) => (
                        <p key={i}>{item}</p>
                    ))}
                </div>

            )}

        </div>

    );

}
    if (msg.intent === "show_profile" && msg.data) {

        const p = msg.data;

        const rows = [
            ["Full Name", p.full_name],
            ["Age", p.age ? `${p.age} yrs` : null],
            ["Gender", p.gender],
            ["Height", p.height ? `${p.height} cm` : null],
            ["Weight", p.weight ? `${p.weight} kg` : null],
            ["Activity Level", p.activity_level ? p.activity_level.replaceAll("_", " ") : null],
            ["Fitness Goal", p.fitness_goal ? p.fitness_goal.replaceAll("_", " ") : null],
            ["Country", p.country],
            ["Region", p.region]
        ];

        return (

            <div className="ai-card profile-snapshot-card">

                <div className="ai-card-header">
                    <span className="ai-card-icon">👤</span>
                    <span>Profile Snapshot</span>
                </div>

                <div className="ai-stat-grid">
                    {rows.map(([label, value]) => (
                        <div className="ai-stat-box" key={label}>
                            <span className="ai-stat-label">{label}</span>
                            <span className="ai-stat-value">{value || "Not set"}</span>
                        </div>
                    ))}
                </div>

                <div className="profile-tags-row">
                    <span className="profile-tag">
                        🥗 {p.dietary_preferences || "No dietary preference set"}
                    </span>
                    <span className="profile-tag warn">
                        ⚠️ {p.allergies || "No allergies on file"}
                    </span>
                    <span className="profile-tag">
                        🩺 {p.medical_condition || "No medical condition on file"}
                    </span>
                </div>

            </div>

        );

    }

    if (msg.intent === "show_progress" && msg.data) {

        const d = msg.data;

        const caloriePercent = Math.min((d.calories_consumed / (d.calorie_goal || 1)) * 100, 100);
        const proteinPercent = Math.min((d.protein_consumed / (d.protein_goal || 1)) * 100, 100);
        const carbsPercent = Math.min((d.carbs_consumed / (d.carbs_goal || 1)) * 100, 100);
        const fatPercent = Math.min((d.fat_consumed / (d.fat_goal || 1)) * 100, 100);
        const isOverLimit = d.calorie_goal > 0 && d.calories_consumed > d.calorie_goal;
        const isProteinOver = d.protein_goal > 0 && d.protein_consumed > d.protein_goal;
        const isCarbsOver = d.carbs_goal > 0 && d.carbs_consumed > d.carbs_goal;
        const isFatOver = d.fat_goal > 0 && d.fat_consumed > d.fat_goal;

        return (

            <div className="ai-card chat-progress-card">

                <div className="ai-card-header">
                    <span className="ai-card-icon">📊</span>
                    <span>Today's Progress</span>
                </div>

                <div className="chat-progress-main">

                    <DonutChart
                        percent={caloriePercent}
                        size={90}
                        strokeWidth={8}
                        color={isOverLimit ? "#D9534F" : "#7BAE7F"}
                        centerValue={`${Math.round(d.calories_consumed)}`}
                        centerLabel={`/ ${Math.round(d.calorie_goal)} kcal`}
                        glow={isOverLimit}
                    />

                    <div className="chat-progress-remaining">
                        <strong>{Math.round(d.calories_remaining)} kcal</strong>
                        <span>Remaining Today</span>
                    </div>

                </div>

                <div className="chat-progress-macros">

                    <div className="chat-progress-macro">
                        <DonutChart percent={proteinPercent} size={54} strokeWidth={5} color={isProteinOver ? "#D9534F" : "#4F8F8B"} centerValue={`${Math.round(d.protein_consumed)}g`} valueFontSize="12px" glow={isProteinOver} />
                        <span>Protein</span>
                        <small>{Math.round(d.protein_consumed)}/{Math.round(d.protein_goal)}g</small>
                    </div>

                    <div className="chat-progress-macro">
                        <DonutChart percent={carbsPercent} size={54} strokeWidth={5} color={isCarbsOver ? "#D9534F" : "#E4B363"} centerValue={`${Math.round(d.carbs_consumed)}g`} valueFontSize="12px" glow={isCarbsOver} />
                        <span>Carbs</span>
                        <small>{Math.round(d.carbs_consumed)}/{Math.round(d.carbs_goal)}g</small>
                    </div>

                    <div className="chat-progress-macro">
                        <DonutChart percent={fatPercent} size={54} strokeWidth={5} color={isFatOver ? "#D9534F" : "#D97D82"} centerValue={`${Math.round(d.fat_consumed)}g`} valueFontSize="12px" glow={isFatOver} />
                        <span>Fat</span>
                        <small>{Math.round(d.fat_consumed)}/{Math.round(d.fat_goal)}g</small>
                    </div>

                </div>

            </div>

        );

    }

    if (msg.intent === "calorie_status" && msg.data) {

        const d = msg.data;
        const percent = Math.min((d.calories_consumed / (d.calorie_goal || 1)) * 100, 100);

        return (

            <div className="ai-card calorie-status-card">

                <div className="ai-card-header">
                    <span className="ai-card-icon">🔥</span>
                    <span>Calorie Status</span>
                </div>

                <div className="chat-progress-main">
                    <DonutChart
                        percent={percent}
                        size={90}
                        strokeWidth={8}
                        color={d.exceeded ? "#D9534F" : "#7BAE7F"}
                        centerValue={`${Math.round(d.calories_consumed)}`}
                        centerLabel={`/ ${Math.round(d.calorie_goal)} kcal`}
                        glow={d.exceeded}
                    />
                </div>

                <div className={`calorie-status-banner ${d.exceeded ? "over" : "ok"}`}>
                    {d.exceeded
                        ? `⚠️ Exceeded by ${Math.round(d.exceeded_by)} kcal`
                        : `On track — ${Math.round(d.calories_remaining)} kcal remaining`}
                </div>

            </div>

        );

    }

    if (msg.intent === "show_meal_history" && msg.data) {

        const meals = msg.data.meals || [];

        const dateGroups = [];
        meals.forEach((meal) => {
            const dateLabel = meal.created_at
                ? new Date(meal.created_at).toLocaleDateString([], {
                    weekday: "long",
                    month: "short",
                    day: "numeric"
                })
                : "Unknown date";
            let group = dateGroups.find(g => g.label === dateLabel);
            if (!group) {
                group = { label: dateLabel, meals: [] };
                dateGroups.push(group);
            }
            group.meals.push(meal);
        });

        const totalCalories = meals.reduce((sum, m) => sum + (m.calories || 0), 0);

        return (

            <div className="ai-card meal-history-chat-card">

                <div className="diet-plan-card-header">
                    <div className="ai-card-header">
                        <span className="ai-card-icon">🍽️</span>
                        <span>Meal History</span>
                    </div>
                    {meals.length > 0 && (
                        <span className="diet-plan-badge">{meals.length} meals</span>
                    )}
                </div>

                {meals.length === 0 ? (

                    <div className="ai-empty-state">No meals logged yet.</div>

                ) : (

                    <>

                        <div className="diet-plan-subtitle">
                            {Math.round(totalCalories)} kcal total across {meals.length} meals
                        </div>

                        <div className="meal-history-chat-list">

                            {dateGroups.map((group) => (

                                <div className="meal-history-date-group" key={group.label}>

                                    <div className="meal-history-date-label">{group.label}</div>

                                    {group.meals.map((meal) => (

                                        <div className="meal-history-chat-row" key={meal.id}>

                                            <div className="meal-history-chat-top">
                                                <h4>{meal.meal_name}</h4>
                                                <div className="meal-history-chat-top-right">
                                                    <span className="meal-history-chat-time">
                                                        {meal.created_at
                                                            ? new Date(meal.created_at).toLocaleTimeString([], {
                                                                hour: "2-digit",
                                                                minute: "2-digit"
                                                            })
                                                            : ""}
                                                    </span>
                                                    <button
                                                        className="meal-history-delete-btn"
                                                        title="Delete this meal"
                                                        onClick={() => requestDeleteMeal(index, meal)}
                                                    >
                                                        ✕
                                                    </button>
                                                </div>
                                            </div>

                                            {meal.portion && (
                                                <p className="meal-history-chat-portion">{meal.portion}</p>
                                            )}

                                            <div className="meal-history-chat-macros">
                                                <span className="chip cal">🔥 {Math.round(meal.calories)}</span>
                                                <span className="chip protein">💪 {Math.round(meal.protein)}g</span>
                                                <span className="chip carbs">🍞 {Math.round(meal.carbs)}g</span>
                                                <span className="chip fat">🥑 {Math.round(meal.fat)}g</span>
                                            </div>

                                        </div>

                                    ))}

                                </div>

                            ))}

                        </div>

                    </>

                )}

            </div>

        );

    }

    if (msg.intent === "show_memories" && msg.data) {

        const memories = msg.data.memories || [];

        return (

            <div className="ai-card profile-snapshot-card">

                <div className="ai-card-header">
                    <span className="ai-card-icon">🧠</span>
                    <span>What I Remember About You</span>
                </div>

                {memories.length === 0 ? (

                    <div className="ai-empty-state">Nothing saved yet — mention a lasting preference or habit and I'll remember it.</div>

                ) : (

                    <div className="ai-stat-grid">
                        {memories.map((m) => (
                            <div className="ai-stat-box" key={m.id}>
                                <span className="ai-stat-label">{m.memory_key.replaceAll(/[_:]/g, " ")}</span>
                                <span className="ai-stat-value">{m.memory_value.replaceAll("_", " ")}</span>
                            </div>
                        ))}
                    </div>

                )}

            </div>

        );

    }

    if (
        msg.intent === "update_profile" &&
        msg.updates &&
        Object.keys(msg.updates).length > 0
    ) {

        const unitSuffix = { age: " yrs", height: " cm", weight: " kg" };
        const changedFields = Object.entries(msg.updates).map(([field, value]) => ({
            key: field,
            label: field.replaceAll("_", " "),
            value: typeof value === "string"
                ? value.replaceAll("_", " ")
                : `${value}${unitSuffix[field] || ""}`
        }));
        const hasGoals = msg.calorieGoal != null;

        return (

            <div className="ai-card profile-update-card">

                <div className="ai-card-header">
                    <span>Profile Updated</span>
                </div>

                <div className="ai-stat-grid">
                    {changedFields.map(f => (
                        <div className="ai-stat-box" key={f.key}>
                            <span className="ai-stat-label">{f.label}</span>
                            <span className="ai-stat-value">{f.value}</span>
                        </div>
                    ))}
                </div>

                {hasGoals && (

                    <div className="ai-stat-grid goals">
                        <div className="ai-stat-box">
                            <span className="ai-stat-label">Calories</span>
                            <span className="ai-stat-value">{msg.calorieGoal} kcal</span>
                        </div>
                        <div className="ai-stat-box">
                            <span className="ai-stat-label">Protein</span>
                            <span className="ai-stat-value">{msg.proteinGoal} g</span>
                        </div>
                        <div className="ai-stat-box">
                            <span className="ai-stat-label">Carbs</span>
                            <span className="ai-stat-value">{msg.carbsGoal} g</span>
                        </div>
                        <div className="ai-stat-box">
                            <span className="ai-stat-label">Fat</span>
                            <span className="ai-stat-value">{msg.fatGoal} g</span>
                        </div>
                    </div>

                )}

            </div>

        );

    }

    return msg.sender === "ai"
        ? <p className="ai-plain-reply">{text}</p>
        : <p>{text}</p>;

})()
}

{msg.additionalData && msg.additionalData.length > 0 && msg.additionalData.map((item, i) => (
    <div key={i}>
        {renderDisplayCard(item.intent, item.data, index, i, requestDeleteMeal)}
    </div>
))}

    {msg.sender === "ai" && (
        <button
            className={
                speakingIndex === index
                    ? "speak-btn speaking"
                    : "speak-btn"
            }
            onClick={() => speakText(getSpokenText(msg), index)}
            title={speakingIndex === index ? "Stop reading" : "Read aloud"}
            aria-label={
                speakingIndex === index
                    ? "Stop reading this message"
                    : "Read this message aloud"
            }
        >
            {speakingIndex === index ? "⏹" : "🔈"}
        </button>
    )}

</div>

)}


                                    {msg.image && (

                                        <img
                                            src={msg.image}
                                            alt="Uploaded meal"
                                            className="chat-image"
                                        />

                                    )}
                                    {msg.audio && (

    <div className="chat-audio-message">


        <button
            className="chat-audio-play"
            onClick={() => {
                const audio = new Audio(msg.audio);
                audio.play();
            }}
        >
            ▶
        </button>


        <div className="chat-audio-wave">

            <span></span>
            <span></span>
            <span></span>
            <span></span>
            <span></span>

        </div>


        <span className="chat-audio-duration">
            {msg.duration}
        </span>


    </div>

)}

                                </div>

                            ))}
                            {isRecording && (
    <div className="recording-indicator">
        🎙️ 
    </div>
)}

{isProcessingAudio && (
    <ThinkingIndicator words={VOICE_THINKING_WORDS} />
)}
                            {isTyping && (

                            <ThinkingIndicator />


                            )}
                             <div ref={chatEndRef}></div>
                            {selectedImage && (

        <div className="chat-message user pending-image">

            <div className="image-chip">

                <span className="image-name">
                    📷 {imageName}
                </span>

                <button
                    className="remove-image-btn"
                    onClick={removeImage}
                >
                    ✕
                </button>

            </div>

        </div>

    )}

                        </div>

                        <div className="input-section">
                            

{isRecording && (

    <div className="recording-preview">

        <div className="recording-dot"></div>

        <span className="recording-text">
            Recording
        </span>

        <span className="recording-time">
            {Math.floor(recordingTime / 60)}:
            {(recordingTime % 60)
                .toString()
                .padStart(2, "0")}
        </span>

    </div>

)}


{audioPreview && (

    <div className="audio-preview">

        <button
            className="audio-play-btn"
            onClick={() => {
                const audio = new Audio(audioPreview.url);
                audio.play();
            }}
        >
            ▶
        </button>


        <div className="audio-progress">

            <span></span>
            <span></span>
            <span></span>
            <span></span>
            <span></span>
            <span></span>

        </div>


        <span className="audio-duration">

            {Math.floor(audioPreview.duration / 60)}:
            {(audioPreview.duration % 60)
                .toString()
                .padStart(2, "0")}

        </span>


        <button
            className="audio-remove-btn"
            onClick={() => setAudioPreview(null)}
        >
            ✕
        </button>


    </div>

)}

                            <input
                                type="text"
                                placeholder="Type your meal or ask a nutrition question"
                                value={message}
                                onChange={(e) => setMessage(e.target.value)}
                                onKeyDown={(e) => {

                                    if (e.key === "Enter") {

                                        sendMessage();

                                    }

                                }}
                            />

                            <input
                                type="file"
                                accept="image/*"
                                id="imageUpload"
                                style={{ display: "none" }}
                                onChange={(e) => {

                                    if (e.target.files.length > 0) {

                                        setSelectedImage(e.target.files[0]);
                                        setImageName(e.target.files[0].name);

                                    }

                                }}
                            />

                            
                        <button
                            className="upload-btn"
                            onClick={() =>
                                document.getElementById("imageUpload").click()
                            }
                            title="Upload image"
                        >
                            <FiPlus />
                        </button>
                        <button
                           className="mic-btn"
                           onMouseDown={startRecording}
                           onMouseUp={stopRecording}
                           onMouseLeave={() => {
                           if (isRecording) stopRecording();
                          }}
                          title="Hold to record"
                            >
                        <FiMic />
                        </button>

                        <button
                            className="send-btn"
                            onClick={sendMessage}
                            title="Send message"
                        >
                            <FiArrowUp />
                        </button>

                        </div>

                    </div>

                </div>

            </div>

            {deleteTarget && (

                <div className="confirm-overlay">

                    <div className="confirm-box">

                        <p>
                            Delete <strong>{deleteTarget.mealName}</strong>{" "}
                            from your meal history?
                        </p>

                        <div className="confirm-buttons">

                            <button
                                className="cancel-btn"
                                onClick={cancelDeleteMeal}
                            >
                                Cancel
                            </button>

                            <button
                                className="confirm-delete-btn"
                                onClick={confirmDeleteMeal}
                            >
                                Delete
                            </button>

                        </div>

                    </div>

                </div>

            )}

            {nutritionAlert && (

                <div className="confirm-overlay">

                    <div className="confirm-box calorie-alert-box">

                        <div className="calorie-alert-header">
                            ⚠️{" "}
                            {nutritionAlert.items.map(i => i.label).join(" & ")}{" "}
                            {nutritionAlert.items.length === 1 ? "Target" : "Targets"} Exceeded
                        </div>

                        <div className="calorie-alert-figures">
                            {nutritionAlert.items.map(item => (
                                <div className="calorie-alert-figure-row" key={item.label}>
                                    <span className="calorie-alert-total">
                                        {item.label}: {item.consumed} / {item.goal} {item.unit}
                                    </span>
                                    <span className="calorie-alert-over">
                                        {item.over_by} {item.unit} over target
                                    </span>
                                </div>
                            ))}
                        </div>

                        {nutritionAlert.guidance && (
                            <div className="calorie-alert-guidance">
                                {nutritionAlert.guidance
                                    .split("\n\n")
                                    .filter(line => !line.startsWith("⚠️"))
                                    .map((line, i) => (
                                        <p key={i}>{line}</p>
                                    ))}
                            </div>
                        )}

                        <div className="confirm-buttons">

                            <button
                                className="confirm-delete-btn calorie-alert-dismiss"
                                onClick={() => setNutritionAlert(null)}
                            >
                                Got it
                            </button>

                        </div>

                    </div>

                </div>

            )}

            {conflictAlert && (

                <div className="confirm-overlay">

                    <div className="confirm-box conflict-alert-box">

                        <div className="conflict-alert-header">
                            ⚠️ {CONFLICT_ALERT_TITLES[conflictAlert.type] || "Profile Conflict"}
                        </div>

                        <div className="conflict-alert-reason">
                            {conflictAlert.reason}
                        </div>

                        <div className="conflict-alert-guidance">
                            <p>{conflictAlert.guidance}</p>
                        </div>

                        {conflictAlert.type === "medical_condition" && (
                            <div className="conflict-alert-disclaimer">
                                This is general guidance, not medical advice — consult your
                                doctor or a registered dietitian for personalized care.
                            </div>
                        )}

                        <div className="confirm-buttons">

                            <button
                                className="confirm-delete-btn conflict-alert-dismiss"
                                onClick={() => setConflictAlert(null)}
                            >
                                Got it
                            </button>

                        </div>

                    </div>

                </div>

            )}

            {planAdjustmentAlert && (

                <div className="confirm-overlay">

                    <div className="confirm-box plan-adjustment-alert-box">

                        <div className="plan-adjustment-alert-header">
                            📋 Diet Plan Rebalanced
                        </div>

                        <p className="plan-adjustment-alert-message">
                            {planAdjustmentAlert.message}
                        </p>

                        <div className="confirm-buttons">

                            <button
                                className="confirm-delete-btn plan-adjustment-alert-dismiss"
                                onClick={() => setPlanAdjustmentAlert(null)}
                            >
                                Got it
                            </button>

                        </div>

                    </div>

                </div>

            )}

            {dailyReminder && (

                <div className="confirm-overlay">

                    <div className="confirm-box daily-reminder-box">

                        <div className="daily-reminder-header">
                            🍽️ Don't Forget to Log Your Meals
                        </div>

                        <div className="daily-reminder-message">
                            {dailyReminder.split("\n\n").map((line, i) => (
                                <p key={i}>{line}</p>
                            ))}
                        </div>

                        <div className="confirm-buttons">

                            <button
                                className="confirm-delete-btn daily-reminder-dismiss"
                                onClick={() => setDailyReminder(null)}
                            >
                                Got it
                            </button>

                        </div>

                    </div>

                </div>

            )}

        </>

    );
}
export default Aiassistant;