import React, { useState, useRef } from 'react';

const VoiceControl = () => {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [response, setResponse] = useState('');
  
  const audioRef = useRef(null);
  
  const startListening = async () => {
    setIsListening(true);
    setTranscript('');
    
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      const audioChunks = [];
      
      // Record audio
      mediaRecorder.ondataavailable = (event) => {
        audioChunks.push(event.data);
      };
      
      mediaRecorder.start();
      
      // Stop recording after 3 seconds (adjust as needed)
      setTimeout(() => {
        mediaRecorder.stop();
        stream.getTracks().forEach(track => track.stop());
        
        const audioBlob = new Blob(audioChunks);
        
        // Send to backend for speech-to-text processing
        sendAudioToSTT(audioBlob);
      }, 3000);
      
    } catch (error) {
      console.error('Error accessing microphone:', error);
      setIsListening(false);
    }
  };

  const sendAudioToSTT = async (audioBlob) => {
    try {
      const formData = new FormData();
      formData.append('audio', audioBlob);
      
      const response = await fetch('/api/voice/stt', {
        method: 'POST',
        body: formData
      });
      
      const result = await response.json();
      setTranscript(result.text);
      
      // Process the text with the agent
      processTranscript(result.text);
      
    } catch (error) {
      console.error('Error sending audio to STT:', error);
      setIsListening(false);
    }
  };

  const processTranscript = async (text) => {
    try {
      // Send the transcribed text to the agent
      const agentResponse = await fetch('/api/agent', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          input: text,
          type: 'voice'
        })
      });
      
      const result = await agentResponse.json();
      setResponse(result.response);
      
      // Speak the response
      speakResponse(result.response);
      
    } catch (error) {
      console.error('Error processing transcript:', error);
    }
  };

  const speakResponse = async (text) => {
    setIsSpeaking(true);
    
    try {
      const response = await fetch('/api/voice/tts?text=' + encodeURIComponent(text), {
        method: 'GET'
      });
      
      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);
      
      const audio = new Audio(audioUrl);
      audio.onended = () => {
        setIsSpeaking(false);
      };
      audio.play();
      
    } catch (error) {
      console.error('Error playing audio:', error);
      setIsSpeaking(false);
    }
  };

  const stopListening = () => {
    setIsListening(false);
  };

  return (
    <div className="voice-control">
      <h3>Voice Control</h3>
      <div className="voice-buttons">
        <button 
          onClick={startListening}
          disabled={isListening}
          className={isListening ? 'listening' : ''}
        >
          {isListening ? 'Listening...' : '🎤 Microphone'}
        </button>
        
        <button 
          onClick={stopListening}
          disabled={!isListening}
        >
          Stop
        </button>
      </div>
      
      {transcript && (
        <div className="transcript">
          <h4>Transcript:</h4>
          <p>{transcript}</p>
        </div>
      )}
      
      {response && (
        <div className="response">
          <h4>Response:</h4>
          <p>{response}</p>
          <button onClick={() => speakResponse(response)} disabled={isSpeaking}>
            {isSpeaking ? 'Speaking...' : '🔊 Speaker'}
          </button>
        </div>
      )}
    </div>
  );
};

export default VoiceControl;