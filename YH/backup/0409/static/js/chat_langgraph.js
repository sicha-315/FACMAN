// ✅ 챗봇 메시지 전송 함수
async function sendLangGraphMessage() {
  const textarea = document.getElementById("chatInput");
  const message = textarea.value.trim();
  if (!message) return;

  const history = document.getElementById("chatHistory");

  // ✅ 새로운 대화 박스 생성
  const chatBox = document.createElement("div");
  chatBox.className = "chat-box";

  // ✅ 사용자 질문 추가
  const userMsg = document.createElement("div");
  userMsg.className = "chat-message user";
  userMsg.textContent = message;
  chatBox.appendChild(userMsg);

  // ✅ 응답 자리 (로딩 중 텍스트 포함)
  const botMsg = document.createElement("div");
  botMsg.className = "chat-message bot";
  botMsg.textContent = "⏳ 답변 생성 중입니다...";
  chatBox.appendChild(botMsg);

  // ✅ 히스토리에 chatBox 추가
  history.appendChild(chatBox);
  history.scrollTop = history.scrollHeight;

  textarea.value = "";

  try {
    const res = await fetch("/chat_langgraph", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message })
    });

    const data = await res.json();
    botMsg.textContent = data.reply;
  } catch (err) {
    botMsg.textContent = "❌ 서버 연결 실패";
    console.error(err);
  }

  history.scrollTop = history.scrollHeight;
}

// ✅ 채팅 기록 초기화 함수
function clearChatHistory() {
  const chatHistory = document.getElementById("chatHistory");
  chatHistory.innerHTML = ""; // 모든 자식 요소 삭제
}

// ✅ 이벤트 바인딩
document.addEventListener("DOMContentLoaded", () => {
  const sendBtn = document.getElementById("chatSendBtn");
  const clearBtn = document.getElementById("chatClearBtn");
  const input = document.getElementById("chatInput");

  if (sendBtn) sendBtn.addEventListener("click", sendLangGraphMessage);
  if (clearBtn) clearBtn.addEventListener("click", clearChatHistory);

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendLangGraphMessage();
    }
  });
});

// ✅ 함수 전역 등록 (HTML에서 직접 호출 가능하도록)
window.sendLangGraphMessage = sendLangGraphMessage;
window.clearChatHistory = clearChatHistory;
