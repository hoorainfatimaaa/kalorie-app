import { useState, useEffect, useRef } from "react";
import Navbar from "../components/Navbar";
import Progress from "../components/Progress";
import MealHistory from "../components/MealHistory";
import "./Aiassistant.css";
import { FiMic, FiChevronLeft, FiChevronRight } from "react-icons/fi";

function Aiassistant() {

    const [message, setMessage] = useState("");
    const [selectedImage, setSelectedImage] = useState(null);
    const [imageName, setImageName] = useState("");
    const [messages, setMessages] = useState([]);
    const [isTyping, setIsTyping] = useState(false);
    const [progressRefresh, setProgressRefresh] = useState(0);
    const [mealUpdated, setMealUpdated] = useState(false);
    const chatEndRef = useRef(null);
    const [isRecording, setIsRecording] = useState(false);
    const [isProcessingAudio, setIsProcessingAudio] = useState(false);
    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);
    const [audioPreview, setAudioPreview] = useState(null);
    const [recordingTime, setRecordingTime] = useState(0);
    const timerRef = useRef(null);
    const [expandedDay, setExpandedDay] = useState(null);
    const [expandedMeal, setExpandedMeal] = useState({});
    const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
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

            const response = await fetch("http://127.0.0.1:5000/chat/history", {
                method: "GET",
                headers: {
                    Authorization: `Bearer ${token}`
                }
            });
            if (!response.ok) {
    console.error("Failed to load history");
    return;
}

const data = await response.json();


if (data.length === 0) {

    setMessages([
        {
            sender: "ai",
            text: "Hello! I'm your personal nutrition assistant. How can I help you today?"
        }
    ]);

} 
else {

    setMessages(
        data.map(msg => ({
            sender: msg.sender,
            text: msg.text || msg.message,
            intent: msg.intent || null,
            plan: msg.plan || null,
            portion: msg.portion || null,
            isEstimated: msg.is_estimated ?? null,
            image: msg.image || null,
            audio: msg.audio || null
        }))
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
                "http://127.0.0.1:5000/chat",
                {
                    method: "POST",

                    headers: {
                        Authorization: `Bearer ${token}`
                    },

                    body: formData
                }
            );

            const data = await response.json();

if (!response.ok) {
    setMessages(prev => [
        ...prev,
        {
            sender: "ai",
            text: data.message || "Something went wrong."
        }
    ]);
    setIsTyping(false);
    return;
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


setMessages(prev => [
    ...prev,
    {
        sender: "ai",
        text: aiText,
        intent: data.reply.intent,
        plan: data.reply.plan || null,
        portion: data.reply.portion || null,
        isEstimated: data.reply.is_estimated ?? null
    }
]);
if (
    data.reply.intent === "meal_log" ||
    data.reply.intent === "meal_update" ||
    data.reply.intent === "meal_delete"

) {
    setProgressRefresh(prev => prev + 1);
    setMealUpdated(prev => !prev);
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
        console.log("start recording")
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
        
        console.log("Audio recorded:", audioBlob);

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
                "http://127.0.0.1:5000/chat/audio",
                {
                    method: "POST",
                    headers: {
                        Authorization: `Bearer ${token}`
                    },
                    body: formData
                }
            );


            const data = await response.json();

            console.log("Backend response:", data);
            
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
        isEstimated: data.reply.is_estimated ?? null
    }
]);
if (
    data.reply?.intent === "meal_log" ||
    data.reply?.intent === "meal_update" ||
    data.reply?.intent === "meal_delete"
) {
    setProgressRefresh(prev => prev + 1);
    setMealUpdated(prev => !prev);
}


if (data.audio) {

    const audio = new Audio(
        `http://127.0.0.1:5000/uploads/${data.audio}`
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

const speakText = async(text)=>{

    try{

        const token = localStorage.getItem("token");


        const response = await fetch(
        "http://127.0.0.1:5000/chat/speak",
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


        if(data.audio){

            const audio = new Audio(
            `http://127.0.0.1:5000/uploads/${data.audio}`
            );

            audio.play();

        }


    }catch(error){

        console.error(
        "Audio generation failed:",
        error
        );

    }

};


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

                               {msg.text && (

<div className="ai-message-content">
{
(() => {

    const text = msg.text;

if (
    msg.intent === "meal_log" ||
    msg.intent === "meal_update"
)
    {

        const meal =
            text.match(/Meal:\s*([\s\S]*?)Meal Type:/)?.[1]?.trim();

        const mealType =
            text.match(/Meal Type:\s*([\s\S]*?)Nutrition:/)?.[1]?.trim();

        const calories =
            text.match(/Calories:\s*(\d+)/)?.[1];

        const protein =
            text.match(/Protein:\s*(\d+)/)?.[1];

        const carbs =
            text.match(/Carbs:\s*(\d+)/)?.[1];

        const fat =
            text.match(/Fat:\s*(\d+)/)?.[1];

        return (

            <div className="meal-log-card">

<div className="meal-log-header">

{
    msg.intent === "meal_update"
        ? "🔄 Meal Updated"
        : "✅ Meal Logged"
}

</div>

                <div className="meal-name">

                    🍽️ {meal}

                </div>

                <div className="meal-type-badge">

                    {mealType}

                </div>

                {msg.portion && (

                    <div className="meal-portion-row">

                        📏 <strong>{msg.portion}</strong>

                    </div>

                )}

                <div className="macro-grid">

                    <div className="macro-box">

                        🔥

                        <strong>{calories}</strong>

                        <span>Calories</span>

                    </div>

                    <div className="macro-box">

                        💪

                        <strong>{protein}g</strong>

                        <span>Protein</span>

                    </div>

                    <div className="macro-box">

                        🍞

                        <strong>{carbs}g</strong>

                        <span>Carbs</span>

                    </div>

                    <div className="macro-box">

                        🥑

                        <strong>{fat}g</strong>

                        <span>Fat</span>

                    </div>

                </div>

                <div className="meal-success">

{
    msg.intent === "meal_update"
        ? "✔ Updated Today's Progress"
        : "✔ Added to Today's Progress"
}

</div>

{msg.isEstimated && (

    <div className="meal-estimated-note">

        📐 Estimated portion — tell me the exact amount for more accurate tracking.

    </div>

)}

            </div>

        );
        

    }
    if (
    msg.intent === "diet_plan_confirmation" &&
    msg.plan
) {

    return (

        <div className="diet-plan-card">

            <div className="diet-plan-header">

                🥗 Weekly Meal Plan

            </div>

            <div className="diet-plan-subtitle">

                Your personalized 7-day meal plan

            </div>

            {msg.plan.map((day) => (

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

                        <span>

                            {
                                expandedDay === day.day
                                    ? "▲"
                                    : "▼"
                            }

                        </span>

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

                                                🍽️ {meal.meal_type}

                                            </span>

                                            <span>

                                                {
                                                    expandedMeal[mealKey]
                                                        ? "▲"
                                                        : "▼"
                                                }

                                            </span>

                                        </div>

                                        {expandedMeal[mealKey] && (

                                            <div className="diet-meal-content">

                                                <h4>

                                                    {meal.meal_name}

                                                </h4>

                                                <p>

                                                    {meal.description}

                                                </p>

                                                <div className="diet-macros">

                                                    <span>

                                                        🔥 {meal.calories}

                                                    </span>

                                                    <span>

                                                        💪 {meal.protein}g

                                                    </span>

                                                    <span>

                                                        🍞 {meal.carbs}g

                                                    </span>

                                                    <span>

                                                        🥑 {meal.fat}g

                                                    </span>

                                                </div>

                                            </div>

                                        )}

                                    </div>

                                );

                            })}

                        </div>

                    )}

                </div>

            ))}
            <div className="diet-plan-question">

    Would you like me to save this plan to your profile?

</div>

        </div>

    );

}
if (msg.intent === "nutrition_question") {

    const lines = text
        .split("\n")
        .map(line => line.trim())
        .filter(line => line !== "");

    const title = lines[0];

    let nutrition = [];
    let why = [];
    let tip = [];

    let section = "why";

    lines.slice(1).forEach(line => {

        const clean = line
            .replace(/[^\w\s:-]/g, "")
            .trim()
            .toLowerCase();

        if (clean.includes("estimated nutrition")) {
            section = "nutrition";
            return;
        }

        if (
            clean === "why" ||
            clean === "notes"
        ) {
            section = "why";
            return;
        }

        if (
            clean === "tip" ||
            clean === "tips"
        ) {
            section = "tip";
            return;
        }

        if (section === "nutrition")
            nutrition.push(line);

        else if (section === "why")
            why.push(line);

        else if (section === "tip")
            tip.push(line);

    });

    return (

        <div className="nutrition-card">

            <div className="nutrition-title">

                {title}

            </div>

            {nutrition.length > 0 && (

                <div className="nutrition-section">

                    <div className="nutrition-section-title">

                        📊 Estimated Nutrition

                    </div>

                    {nutrition.map((item, i) => (

                        <div
                            key={i}
                            className="nutrition-item"
                        >
                            {item}
                        </div>

                    ))}

                </div>

            )}

            {why.length > 0 && (

                <div className="nutrition-section">

                    <div className="nutrition-section-title">

                        💡 Why

                    </div>

                    {why.map((item, i) => (

                        <div
                            key={i}
                            className="nutrition-item"
                        >
                            {item}
                        </div>

                    ))}

                </div>

            )}

            {tip.length > 0 && (

                <div className="nutrition-section">

                    <div className="nutrition-section-title">

                        ✅ Tip

                    </div>

                    {tip.map((item, i) => (

                        <div
                            key={i}
                            className="nutrition-item"
                        >
                            {item}
                        </div>

                    ))}

                </div>

            )}

        </div>

    );

}
    return <p>{text}</p>;

})()
}

    {msg.sender === "ai" && (
        <button
            className="speak-btn"
            onClick={() =>
                speakText(
                    typeof msg.text === "object"
                        ? msg.text.reply
                        : msg.text
                )
            }
        >
            🔈
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
    <div className="thinking-text">
        Processing voice message...
    </div>
)}
                            {isTyping && (

                            <div className="thinking-text">
                           Thinking...
                            </div>


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
                            📷
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
                            ➤
                        </button>

                        </div>

                    </div>

                    <div
                        className={`mobile-sidebar-overlay ${mobileSidebarOpen ? "active" : ""}`}
                        onClick={() => setMobileSidebarOpen(false)}
                    ></div>
                    <button
                        className={`mobile-sidebar-toggle ${mobileSidebarOpen ? "open" : ""}`}
                        onClick={() => setMobileSidebarOpen(prev => !prev)}
                        aria-label={mobileSidebarOpen ? "Close progress panel" : "Open progress panel"}
                        title={mobileSidebarOpen ? "Close" : "Today's Progress & Meal History"}
                    >
                        {mobileSidebarOpen ? <FiChevronLeft /> : <FiChevronRight />}
                    </button>

                    <div className={`assistant-sidebar ${mobileSidebarOpen ? "mobile-open" : ""}`}>


                    <div className="progress-card-wrapper">

                        <Progress
                        compact
                        refresh={progressRefresh}
                         />

                            </div>


                    <div className="meal-history-wrapper">

                        <MealHistory mealUpdated={mealUpdated}
                        setProgressRefresh={setProgressRefresh} />

                    </div>


                    </div>

                </div>

            </div>

        </>

    );
}
export default Aiassistant;