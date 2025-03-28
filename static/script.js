let mediaRecorder;
let audioChunks = [];
let isProcessing = false;
let isRecording = false;

// DOM Elements
const speakButton = document.getElementById("speakButton");
const messageInput = document.getElementById("messageInput");
const chatContainer = document.getElementById("chatContainer");
const statusText = document.getElementById("status");
const spinner = document.getElementById("spinner");
const languageSelect = document.getElementById("language");
const selectedLanguageDisplay = document.getElementById("selectedLanguageDisplay");
const newChatButton = document.getElementById("newChatButton");
const settingsButton = document.getElementById("settingsButton");
const settingsModal = document.getElementById("settingsModal");
const closeSettingsButton = document.getElementById("closeSettingsButton");
const saveSettingsButton = document.getElementById("saveSettingsButton");
const transcriptionModelSelect = document.getElementById("transcriptionModel");
const responseModelSelect = document.getElementById("responseModel");

// Language display mapping
const languageInfo = {
  "sv": { name: "Swedish", flag: "se" },
  "en": { name: "English", flag: "gb" },
  "fi": { name: "Finnish", flag: "fi" },
  "no": { name: "Norwegian", flag: "no" },
  "da": { name: "Danish", flag: "dk" },
  "es": { name: "Spanish", flag: "es" },
  "fr": { name: "French", flag: "fr" },
  "de": { name: "German", flag: "de" },
  "it": { name: "Italian", flag: "it" },
  "ja": { name: "Japanese", flag: "jp" },
  "ko": { name: "Korean", flag: "kr" },
  "zh": { name: "Chinese", flag: "cn" },
  "ru": { name: "Russian", flag: "ru" },
  "": { name: "Auto Detect", flag: null }
};

// Update the selected language display when the language is changed
languageSelect.addEventListener("change", () => {
  const selectedValue = languageSelect.value;
  const language = languageInfo[selectedValue];
  
  if (language) {
    if (language.flag) {
      selectedLanguageDisplay.innerHTML = `<span class="flag-icon flag-icon-${language.flag}"></span> ${language.name}`;
    } else {
      selectedLanguageDisplay.innerHTML = language.name;
    }
  }
});

// Function to add a message to the chat
function addMessage(text, isUser = false) {
  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${isUser ? "user-message" : "ai-message"}`;
  messageDiv.textContent = text;
  
  // Add message with animation
  messageDiv.style.opacity = 0;
  chatContainer.appendChild(messageDiv);
  gsap.to(messageDiv, {opacity: 1, duration: 0.3});
  
  // Scroll to bottom
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Function to add a tool output message to the chat
function addToolOutput(text) {
  const toolMessageElement = document.createElement("div");
  toolMessageElement.className = "tool-message";
  
  const toolOutputElement = document.createElement("div");
  toolOutputElement.className = "tool-output";
  toolOutputElement.innerHTML = text;
  
  toolMessageElement.appendChild(toolOutputElement);
  
  // Add tool output with animation
  toolMessageElement.style.opacity = 0;
  chatContainer.appendChild(toolMessageElement);
  gsap.to(toolMessageElement, {opacity: 1, duration: 0.3});
  
  // Scroll to bottom
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Function to send a text message
async function sendTextMessage(text) {
  if (!text.trim()) return;
  
  // Add user message to chat
  addMessage(text, true);
  
  // Clear input field
  messageInput.value = "";
  
  // Show processing state
  statusText.textContent = "⏳ Processing...";
  spinner.style.display = "block";
  messageInput.disabled = true;
  speakButton.disabled = true;
  
  try {
    // Get the selected language
    const selectedLanguage = languageSelect.value;
    
    const response = await fetch("/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        message: text,
        language: selectedLanguage
      })
    });
    
    const result = await response.json();
    
    // Check if we have an AI response (from text input) or a response (from older code)
    const aiResponse = result.ai_response || result.response;
    
    if (aiResponse) {
      // Check if the response contains tool output (indicated by ✅ or ❌)
      if (aiResponse.includes("✅ Tool") || aiResponse.includes("❌ Tool")) {
        // Split the response into the AI part and the tool output part
        const parts = aiResponse.split(/\n\n(✅ Tool|\❌ Tool)/);
        
        if (parts.length > 1) {
          // Add the AI response part
          addMessage(parts[0]);
          
          // Add the tool output with special formatting
          setTimeout(() => {
            const toolOutput = parts.slice(1).join("");
            addToolOutput(toolOutput);
          }, 500);
        } else {
          // If splitting didn't work, just add the whole response
          addMessage(aiResponse);
        }
      } else {
        // No tool output, just add the response
        addMessage(aiResponse);
      }
      statusText.textContent = "✅ Response received";
    } else {
      statusText.textContent = "❌ Failed to get response";
      console.error("Error:", result.error);
    }
  } catch (error) {
    statusText.textContent = "❌ Error: " + error.message;
    console.error("Error sending message:", error);
  } finally {
    // Reset UI state
    spinner.style.display = "none";
    messageInput.disabled = false;
    speakButton.disabled = false;
    messageInput.focus();
  }
}

// Handle text input submission
messageInput.addEventListener("keypress", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    const text = messageInput.value.trim();
    if (text) {
      sendTextMessage(text);
    }
  }
});

// Handle recording audio
speakButton.addEventListener("click", async () => {
  if (isProcessing) return; // Prevent actions while processing
  
  if (isRecording) {
    // Stop recording
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
      statusText.textContent = "🛑 Stopped recording";
    }
    isRecording = false;
    speakButton.classList.remove("recording");
    speakButton.innerHTML = '<i class="fas fa-microphone"></i>';
  } else {
    // Start recording
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      audioChunks = [];
      
      mediaRecorder.ondataavailable = e => {
        if (e.data.size > 0) {
          audioChunks.push(e.data);
        }
      };
      
      mediaRecorder.onstop = async () => {
        isProcessing = true;
        
        // Show processing state
        spinner.style.display = "block";
        speakButton.disabled = true;
        messageInput.disabled = true;
        
        const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
        const formData = new FormData();
        formData.append("audio", audioBlob, "recording.webm");
        
        // Add language if selected
        const selectedLanguage = languageSelect.value;
        if (selectedLanguage) {
          formData.append("language", selectedLanguage);
        }
        
        statusText.textContent = "⏳ Transcribing...";
        
        try {
          const response = await fetch("/transcribe", {
            method: "POST",
            body: formData
          });
          
          const result = await response.json();
          
          if (result.text) {
            // Add user's transcribed message to chat
            addMessage(result.text, true);
            statusText.textContent = "✅ Transcription complete!";
            
            // If there's an AI response, add it to the chat
            if (result.ai_response) {
              // Add a slight delay to make the conversation feel more natural
              setTimeout(() => {
                // Check if the response contains tool output (indicated by ✅ or ❌)
                if (result.ai_response.includes("✅ Tool") || result.ai_response.includes("❌ Tool")) {
                  // Split the response into the AI part and the tool output part
                  const parts = result.ai_response.split(/\n\n(✅ Tool|\❌ Tool)/);
                  
                  if (parts.length > 1) {
                    // Add the AI response part
                    addMessage(parts[0]);
                    
                    // Add the tool output with special formatting
                    setTimeout(() => {
                      const toolOutput = parts.slice(1).join("");
                      addToolOutput(toolOutput);
                    }, 500);
                  } else {
                    // If splitting didn't work, just add the whole response
                    addMessage(result.ai_response);
                  }
                } else {
                  // No tool output, just add the response
                  addMessage(result.ai_response);
                }
              }, 500);
            }
          } else {
            statusText.textContent = "❌ Failed to transcribe";
            console.error("Error:", result.error || "Unknown error");
          }
        } catch (error) {
          statusText.textContent = "❌ Error: " + error.message;
          console.error("Transcription error:", error);
        } finally {
          // Reset UI state
          spinner.style.display = "none";
          speakButton.disabled = false;
          messageInput.disabled = false;
          isProcessing = false;
          
          // Close all tracks to properly release the microphone
          stream.getTracks().forEach(track => track.stop());
        }
      };
      
      mediaRecorder.start();
      isRecording = true;
      speakButton.classList.add("recording");
      speakButton.innerHTML = '<i class="fas fa-stop"></i>';
      statusText.textContent = "🎙️ Recording...";
    } catch (error) {
      statusText.textContent = "❌ Error accessing microphone: " + error.message;
      console.error("Microphone access error:", error);
    }
  }
});

// Settings functionality
let models = [];
let currentSettings = {};

// Fetch models from the server
async function fetchModels() {
  try {
    const response = await fetch("/models");
    const data = await response.json();
    models = data.models || [];
    populateModelDropdowns();
  } catch (error) {
    console.error("Error fetching models:", error);
  }
}

// Fetch current settings from the server
async function fetchSettings() {
  try {
    const response = await fetch("/settings");
    currentSettings = await response.json();
    updateSettingsUI();
  } catch (error) {
    console.error("Error fetching settings:", error);
  }
}

// Populate model dropdowns
function populateModelDropdowns() {
  // Clear existing options
  transcriptionModelSelect.innerHTML = "";
  responseModelSelect.innerHTML = "";
  
  // Add transcription models
  const transcriptionModels = models.filter(model => model.can_transcribe);
  transcriptionModels.forEach(model => {
    const option = document.createElement("option");
    option.value = model.model;
    option.textContent = `${model.provider} - ${model.model}`;
    if (model.model === currentSettings.transcription_model) {
      option.selected = true;
    }
    transcriptionModelSelect.appendChild(option);
  });
  
  // Add response models
  models.forEach(model => {
    const option = document.createElement("option");
    option.value = model.model;
    option.textContent = `${model.provider} - ${model.model}${model.multimodal ? " (Multimodal)" : ""}`;
    if (model.model === currentSettings.response_model) {
      option.selected = true;
    }
    responseModelSelect.appendChild(option);
  });
}

// Update settings UI based on current settings
function updateSettingsUI() {
  // Set selected options in dropdowns
  if (transcriptionModelSelect.options.length > 0) {
    for (let i = 0; i < transcriptionModelSelect.options.length; i++) {
      if (transcriptionModelSelect.options[i].value === currentSettings.transcription_model) {
        transcriptionModelSelect.selectedIndex = i;
        break;
      }
    }
  }
  
  if (responseModelSelect.options.length > 0) {
    for (let i = 0; i < responseModelSelect.options.length; i++) {
      if (responseModelSelect.options[i].value === currentSettings.response_model) {
        responseModelSelect.selectedIndex = i;
        break;
      }
    }
  }
  
  // Check if the selected models are valid
  validateSelectedModels();
}

// Validate selected models
function validateSelectedModels() {
  const transcriptionModel = transcriptionModelSelect.value;
  
  // Find the model info
  const transcriptionModelInfo = models.find(model => model.model === transcriptionModel);
  
  // Check if the transcription model can transcribe
  if (transcriptionModelInfo && !transcriptionModelInfo.can_transcribe) {
    statusText.textContent = "⚠️ Warning: Selected transcription model cannot transcribe audio";
  }
}

// Save settings to the server
async function saveSettings() {
  const transcriptionModel = transcriptionModelSelect.value;
  const responseModel = responseModelSelect.value;
  
  // Validate models before saving
  const transcriptionModelInfo = models.find(model => model.model === transcriptionModel);
  if (!transcriptionModelInfo) {
    statusText.textContent = "❌ Error: Transcription model not found";
    return;
  }
  
  if (!transcriptionModelInfo.can_transcribe) {
    if (!confirm("The selected transcription model cannot transcribe audio. Are you sure you want to continue?")) {
      return;
    }
  }
  
  const newSettings = {
    transcription_model: transcriptionModel,
    response_model: responseModel
  };
  
  try {
    spinner.style.display = "block";
    statusText.textContent = "⏳ Saving settings...";
    
    const response = await fetch("/settings", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(newSettings)
    });
    
    const result = await response.json();
    
    if (result.success) {
      currentSettings = result.settings;
      statusText.textContent = "✅ Settings saved successfully";
      settingsModal.classList.add("hidden");
    } else {
      statusText.textContent = "❌ Failed to save settings";
      console.error("Error:", result.error);
    }
  } catch (error) {
    statusText.textContent = "❌ Error: " + error.message;
    console.error("Error saving settings:", error);
  } finally {
    spinner.style.display = "none";
  }
}

// Event listeners for settings
settingsButton.addEventListener("click", () => {
  settingsModal.classList.remove("hidden");
});

closeSettingsButton.addEventListener("click", () => {
  settingsModal.classList.add("hidden");
});

saveSettingsButton.addEventListener("click", saveSettings);

// Close modal when clicking outside
settingsModal.addEventListener("click", (e) => {
  if (e.target === settingsModal) {
    settingsModal.classList.add("hidden");
  }
});

// Focus input field on page load and fetch models and settings
window.addEventListener("load", () => {
  messageInput.focus();
  fetchModels();
  fetchSettings();
});

// Handle new chat button click
newChatButton.addEventListener("click", () => {
  // Clear the chat container except for the welcome message
  while (chatContainer.childNodes.length > 0) {
    chatContainer.removeChild(chatContainer.lastChild);
  }
  
  // Add welcome message
  const welcomeMessage = document.createElement("div");
  welcomeMessage.className = "message ai-message";
  welcomeMessage.textContent = "Hello! How can I help you today? You can type a message or click the microphone button to speak.";
  chatContainer.appendChild(welcomeMessage);
  
  // Clear input field and reset status
  messageInput.value = "";
  statusText.textContent = "Type a message or click the microphone to speak";
  
  // Add animation effect
  gsap.fromTo(welcomeMessage, {opacity: 0}, {opacity: 1, duration: 0.5});
  
  // Focus on input field
  messageInput.focus();
});
