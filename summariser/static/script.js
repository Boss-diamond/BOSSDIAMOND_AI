document.addEventListener("DOMContentLoaded", () => {
    const chatWindow = document.getElementById("chat-window");
    const messageInput = document.getElementById("message-input");
    const fileInput = document.getElementById("file-upload");
    const sendButton = document.getElementById("send-button");

    // Append message to chat window
    function appendMessage(sender, text) {
        const msgDiv = document.createElement("div");
        msgDiv.classList.add("message", sender, "p-2", "rounded", "max-w-[75%]");

        if (sender === "user") {
            msgDiv.classList.add("self-end", "bg-blue-500", "text-white");
        } else {
            msgDiv.classList.add("self-start", "bg-gray-200");
        }

        msgDiv.innerText = text;
        chatWindow.appendChild(msgDiv);
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    // Immediate file upload
    fileInput.addEventListener("change", async () => {
        const file = fileInput.files[0];
        if (!file) return;

        appendMessage("user", `📎 Uploaded: ${file.name}`);
        appendMessage("ai", "⏳ Summarizing your document, please wait...");

        const formData = new FormData();
        formData.append("file", file);

        try {
            const response = await fetch("/chat", {
                method: "POST",
                body: formData,
            });

            const data = await response.json();

            if (data.summary) {
                appendMessage("ai", "📘 Summary:\n" + data.summary);
            } else if (data.error) {
                appendMessage("ai", "❌ Error: " + data.error);
            } else {
                appendMessage("ai", "⚠️ No summary returned.");
            }
        } catch (err) {
            appendMessage("ai", "❌ Error: Could not summarize the document.");
        } finally {
            fileInput.value = ""; // reset input
        }
    });

    // Normal chat message
    sendButton.addEventListener("click", sendMessage);
    messageInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") sendMessage();
    });

    async function sendMessage() {
        const message = messageInput.value.trim();
        if (!message) return;

        appendMessage("user", message);

        const formData = new FormData();
        formData.append("message", message);

        try {
            const response = await fetch("/chat", {
                method: "POST",
                body: formData,
            });
            const data = await response.json();

            if (data.ai) appendMessage("ai", data.ai);
            if (data.error) appendMessage("ai", "❌ " + data.error);
        } catch (err) {
            appendMessage("ai", "❌ Error: Could not get a response.");
        }

        messageInput.value = "";
    }
});
