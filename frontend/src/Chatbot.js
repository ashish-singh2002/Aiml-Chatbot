import React, { useState, useEffect, useCallback, useRef } from "react";
import axios from "axios";
import "@fortawesome/fontawesome-free/css/all.min.css";
import "./App.css";

const Chatbot = () => {
  const [messages, setMessages] = useState(() => {
    const savedMessages = localStorage.getItem("messages");
    return savedMessages ? JSON.parse(savedMessages) : [];
  });
  const [userMessage, setUserMessage] = useState("");
  const [sessionId, setSessionId] = useState(
    localStorage.getItem("session_id") || null
  );
  const [error, setError] = useState(null);
  const [isListening, setIsListening] = useState(false); // Speech-to-Text state
  const chatBoxRef = useRef(null);
  const recognitionRef = useRef(null);

  // Generate a new session ID
  const generateNewSessionId = () => {
    return "session_" + new Date().getTime();
  };

  // Initialize a new session or use the existing one
  const initializeSession = useCallback(() => {
    const newSessionId = sessionId || generateNewSessionId();
    setSessionId(newSessionId);
    localStorage.setItem("session_id", newSessionId);

    // Initialize messages with a greeting
    const initialMessages = [
      { text: "Hello! How can I assist you today?😊", sender: "bot" },
    ];
    setMessages(initialMessages);
    localStorage.setItem("messages", JSON.stringify(initialMessages));
  }, [sessionId]);

  // Check and initialize session on mount
  useEffect(() => {
    if (!sessionId) {
      initializeSession();
    }
  }, [sessionId, initializeSession]);

  // Save messages to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem("messages", JSON.stringify(messages));
  }, [messages]);

  // Scroll to the bottom of the chat-box when new messages arrive
  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = async () => {
    if (userMessage.trim() === "") return;

    setMessages((prevMessages) => [
      ...prevMessages,
      { text: `User: ${userMessage}`, sender: "user" },
    ]);

    try {
      const response = await axios.post(
        "http://172.16.1.226:5005/webhooks/rest/webhook",
        
        {
          message: userMessage,
          sender: sessionId,
        }
      );

      const botMessages = response.data;
      botMessages.forEach((message) => {
        setMessages((prevMessages) => [
          ...prevMessages,
          { text: `Bot: ${message.text}`, sender: "bot" },
        ]);

        // Speak the bot's response for each message
        speakBotResponse(message.text);
      });

      setError(null);
    } catch (error) {
      console.error("Error sending message:", error);
      setError("Sorry, something went wrong. Please try again.");
    }

    setUserMessage("");
  };

  // Handle pressing Enter key to send message
  const handleKeyPress = (e) => {
    if (e.key === "Enter") {
      sendMessage();
    }
  };

  // Speech Synthesis for voice output
  const speakBotResponse = (text) => {
    if ("speechSynthesis" in window) {
      const speech = new window.SpeechSynthesisUtterance(text);
      speech.lang = "en-US";

      speech.onend = () => {
        console.log("Speech has ended.");
      };

      if (
        navigator.userAgent.includes("iPhone") ||
        navigator.userAgent.includes("iPad")
      ) {
        const handleInteraction = () => {
          window.speechSynthesis.speak(speech);
          document.removeEventListener("click", handleInteraction);
        };
        document.addEventListener("click", handleInteraction);
      } else {
        window.speechSynthesis.speak(speech);
      }
    } else {
      console.log("Speech synthesis not supported in this browser.");
    }
  };

  // Initialize Speech Recognition (for cross-browser support)
  useEffect(() => {
    if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
      const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition;

      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.lang = "en-US";

      recognitionRef.current.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setUserMessage(transcript); // Set spoken text as input
      };

      recognitionRef.current.onend = () => {
        setIsListening(false);
      };
    } else {
      console.log("Speech recognition is not supported in this browser.");
    }
  }, []);

  // Start/Stop Speech Recognition
  const toggleListening = () => {
    if (!recognitionRef.current) {
      alert("Speech recognition is not supported in this browser.");
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      recognitionRef.current.start();
      setIsListening(true);
    }
  };

  // WhatsApp link with predefined message
  const phoneNumber = "919911855726";
  const message = "Hello, Maxtra Team";
  const whatsappLink = `https://wa.me/${phoneNumber}?text=${encodeURIComponent(
    message
  )}`;

  return (
    <div className="chat-container">
      <div className="chat-header">
        <button
          className="reset-session-btn"
          onClick={() => {
            localStorage.removeItem("session_id");
            localStorage.removeItem("messages"); // Clear message history
            initializeSession(); // Start a new session
          }}
          title="Start New Session"
        >
          🔄
        </button>
        <div className="whatsapp-chat-btn">
          <a href={whatsappLink} target="_blank" rel="noopener noreferrer">
            <button className="whatsapp-btn">
              <i className="fab fa-whatsapp"></i>
            </button>
          </a>
        </div>
      </div>

      <div className="chat-box" ref={chatBoxRef}>
        <div className="message-wrapper">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`message ${message.sender === "user" ? "user" : "bot"}`}
            >
              {message.text}
            </div>
          ))}
        </div>
      </div>

      <div className="chat-input">
        <input
          type="text"
          value={userMessage}
          onChange={(e) => setUserMessage(e.target.value)}
          onKeyDown={handleKeyPress}
          placeholder="Type your message here..."
        />
        <button onClick={sendMessage}>➤</button>
        <button className="mic-btn" onClick={toggleListening}>
          {isListening ? "🎤 Recording..." : "🎙️ Voice"}
        </button>
      </div>
      {error && <div className="error-message">{error}</div>}
    </div>
  );
};

export default Chatbot;
