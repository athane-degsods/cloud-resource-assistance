const sendBtn = document.getElementById("sendBtn");
const message = document.getElementById("message");
const log = document.getElementById("log");

sendBtn.addEventListener("click", () => {
    const userMessage = message.value;

    log.innerHTML += "<p><strong>You:</strong> " + userMessage + "</p>";

    fetch("/chat", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            message: userMessage,
        }),
    })
        .then(async (response) => {
            const data = await response.json().catch(() => null);
            if (!response.ok) {
                const err =
                    (data && (data.error || data.summary)) ||
                    "HTTP " + response.status;
                throw new Error(err);
            }
            return data;
        })
        .then((data) => {
            log.innerHTML +=
                "<p><strong>AI:</strong> " +
                (data.readable_response || JSON.stringify(data)) +
                "</p>";
        })
        .catch((err) => {
            log.innerHTML +=
                "<p><strong>Error:</strong> " + err.message + "</p>";
            console.error(err);
        });
});
