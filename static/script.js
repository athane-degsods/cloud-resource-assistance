const sendBtn = document.getElementById("sendBtn");
const message = document.getElementById("message");
const log = document.getElementById("log");
const recommendations = document.getElementById("recommendations");

let requestId = "";

function appendLog(html) {
    log.innerHTML += html;
    log.scrollTop = log.scrollHeight;
}

function clearRecommendations() {
    if (recommendations) {
        recommendations.innerHTML = "";
    }
}

function focusComposer() {
    message.focus();
}

function postDecide(decision, pathId) {
    const body = {
        request_id: requestId,
        decision: decision,
    };
    if (pathId) {
        body.path_id = pathId;
    }

    return fetch("/decide", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
    }).then(async (response) => {
        const data = await response.json().catch(() => null);
        if (!response.ok) {
            const err =
                (data && (data.message || data.error)) ||
                "HTTP " + response.status;
            throw new Error(err);
        }
        return data;
    });
}

function showDecision(data) {
    const results = (data.results || []).join("<br>");
    appendLog(
        "<div class=\"decision\">" +
            "<p><strong>Decision:</strong> " +
            (data.status || "unknown") +
            "<br>" +
            (data.message || "") +
            (results ? "<br>" + results : "") +
            "</p>" +
            "</div>"
    );
}

function renderPaths(paths) {
    clearRecommendations();
    if (!recommendations || !paths || !paths.length) {
        return;
    }

    paths.forEach((path) => {
        const card = document.createElement("div");
        card.className = "card";
        card.innerHTML =
            "<p><strong>" +
            (path.title || path.id) +
            "</strong></p>" +
            "<p class=\"risk\">Risk: " +
            (path.risk || "n/a") +
            "</p>" +
            "<p>" +
            (path.reason || "") +
            "</p>";

        const approveBtn = document.createElement("button");
        approveBtn.type = "button";
        approveBtn.textContent = "Approve";
        approveBtn.addEventListener("click", () => {
            window.approvePath(path.id);
        });
        card.appendChild(approveBtn);
        recommendations.appendChild(card);
    });

    const controls = document.createElement("div");
    controls.style.marginTop = "10px";

    const rejectBtn = document.createElement("button");
    rejectBtn.type = "button";
    rejectBtn.textContent = "Reject";
    rejectBtn.addEventListener("click", () => window.rejectRequest());

    const editBtn = document.createElement("button");
    editBtn.type = "button";
    editBtn.textContent = "Edit";
    editBtn.style.marginLeft = "8px";
    editBtn.addEventListener("click", () => window.editRequest());

    controls.appendChild(rejectBtn);
    controls.appendChild(editBtn);
    recommendations.appendChild(controls);
}

function sendMessage() {
    const userMessage = message.value.trim();

    if (userMessage === "") {
        alert("Please enter a request.");
        return;
    }

    appendLog("<p><strong>You:</strong> " + userMessage + "</p>");
    clearRecommendations();
    message.value = "";

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
            requestId = data.request_id || "";

            if (data.pii_warning) {
                appendLog(
                    "<p><strong>Privacy warning:</strong> " +
                        data.pii_warning +
                        "</p>"
                );
            }

            appendLog(
                "<p><strong>AI:</strong> " +
                    (data.readable_response || "No response received.") +
                    "</p>"
            );

            const paths =
                (data.model_response && data.model_response.paths) || [];
            if (paths.length > 0) {
                renderPaths(paths);
            } else {
                clearRecommendations();
                requestId = "";
            }
            focusComposer();
        })
        .catch((err) => {
            console.error(err);
            appendLog(
                "<p><strong>Error:</strong> " + err.message + "</p>"
            );
            focusComposer();
        });
}

sendBtn.addEventListener("click", sendMessage);
message.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
        event.preventDefault();
        sendMessage();
    }
});

window.approvePath = function approvePath(pathId) {
    if (!requestId) {
        appendLog("<p><strong>Error:</strong> No active request_id.</p>");
        return;
    }

    postDecide("approve", pathId)
        .then((data) => {
            showDecision(data);
            clearRecommendations();
            if (data.status === "executed") {
                requestId = "";
            }
            focusComposer();
        })
        .catch((err) => {
            console.error(err);
            appendLog(
                "<p><strong>Error:</strong> " + err.message + "</p>"
            );
            focusComposer();
        });
};

window.rejectRequest = function rejectRequest() {
    if (!requestId) {
        appendLog("<p><strong>Error:</strong> No active request_id.</p>");
        return;
    }

    postDecide("reject")
        .then((data) => {
            showDecision(data);
            requestId = "";
            clearRecommendations();
            focusComposer();
        })
        .catch((err) => {
            console.error(err);
            appendLog(
                "<p><strong>Error:</strong> " + err.message + "</p>"
            );
            focusComposer();
        });
};

window.editRequest = function editRequest() {
    if (!requestId) {
        appendLog("<p><strong>Error:</strong> No active request_id.</p>");
        return;
    }

    postDecide("edit")
        .then((data) => {
            showDecision(data);
            clearRecommendations();
            focusComposer();
        })
        .catch((err) => {
            console.error(err);
            appendLog(
                "<p><strong>Error:</strong> " + err.message + "</p>"
            );
            focusComposer();
        });
};
