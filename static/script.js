const sendBtn = document.getElementById("sendBtn");
const message = document.getElementById("message");
const log = document.getElementById("log");

// Store the current request ID
let requestId = "";

// Send button click
sendBtn.addEventListener("click", () => {

    const userMessage = message.value.trim();

    // Check if input is empty
    if (userMessage === "") {
        alert("Please enter a request.");
        return;
    }

    // Display user message
    log.innerHTML +=
        "<p><strong>You:</strong> " + userMessage + "</p>";

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

        // Save request ID
        requestId = data.request_id || "";

        // Display AI response
        log.innerHTML +=
            "<p><strong>AI:</strong> " +
            (data.readable_response || "No response received.") +
            "</p>";

        // Display recommendation paths
        if (
            data.model_response &&
            data.model_response.paths &&
            data.model_response.paths.length > 0
        ) {

            data.model_response.paths.forEach((path) => {

                log.innerHTML +=
                    "<p>" +
                    "<strong>Title:</strong> " + path.title + "<br>" +
                    "<strong>Risk:</strong> " + path.risk + "<br>" +
                    "<strong>Reason:</strong> " + path.reason + "<br>" +

                    "<button onclick=\"approvePath('" + path.id + "')\">" +
                    "Approve" +
                    "</button>" +

                    "</p><hr>";

            });

        }

        // Reject and Edit buttons
        log.innerHTML +=

            "<button onclick=\"rejectRequest()\">" +
            "Reject" +
            "</button> " +

            "<button onclick=\"editRequest()\">" +
            "Edit" +
            "</button><br><br>";

    })

    .catch((err) => {

        console.error(err);

        log.innerHTML +=
            "<p><strong>Error:</strong> " +
            err.message +
            "</p>";

    });

});


// Approve button
function approvePath(pathId) {

    console.log("Request ID:", requestId);
    console.log("Path ID:", pathId);

    alert(
        "Approve button clicked.\n\n" +
        "Backend /decide endpoint is not implemented yet."
    );

}


// Reject button
function rejectRequest() {

    console.log("Request ID:", requestId);

    // Clear input box
    message.value = "";

    alert(
        "Reject button clicked.\n\n" +
        "Backend /decide endpoint is not implemented yet."
    );

}


// Edit button
function editRequest() {

    console.log("Request ID:", requestId);

    alert(
        "Edit button clicked.\n\n" +
        "Modify your request and click Send again."
    );

    // Keep cursor in input box
    message.focus();

}