const sendBtn = document.getElementById("sendBtn");
const message = document.getElementById("message");
const log = document.getElementById("log");

sendBtn.addEventListener("click", () => {

    const userMessage = message.value;

    log.innerHTML += "<p><strong>You:</strong> " + userMessage + "</p>";

    fetch("/chat", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            message: userMessage
        })
    })
    .then(response => response.json())
    .then(data => {
        log.innerHTML += "<p><strong>AI:</strong> " + data.readable_response + "</p>";
    });

});