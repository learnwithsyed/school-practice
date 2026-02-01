let questions = [];
let currentIndex = 0;
let correctAnswer = "";
let score = 0;
let countdown; // store interval globally

// START PRACTICE
function startPractice() {
    const selectedClass = document.getElementById("class").value;
    const selectedSubject = document.getElementById("subject").value;

    if (selectedClass === "" || selectedSubject === "") {
        alert("Please select Class and Subject");
        return;
    }

    fetch(`/get-questions?class=${selectedClass}&subject=${selectedSubject}`)
        .then(res => res.json())
        .then(data => {
            if (!data.questions || data.questions.length === 0) {
                alert("No questions available for this selection");
                return;
            }

            questions = data.questions;
            currentIndex = 0;
            score = 0;

            document.getElementById("score").innerText = "Score: 0";
            document.getElementById("questionBox").style.display = "block";
            document.querySelector(".options").style.display = "block";
            document.getElementById("result").innerText = "";

            loadQuestion();
        })
        .catch(error => {
            console.error("Error:", error);
            alert("Server error. Please try again.");
        });
}

// LOAD QUESTION
function loadQuestion() {
    const q = questions[currentIndex];
    document.getElementById("questionText").innerText =
        `Q${currentIndex + 1}. ${q.question}`;
    document.getElementById("optA").innerText = q.options.A;
    document.getElementById("optB").innerText = q.options.B;
    document.getElementById("optC").innerText = q.options.C;
    document.getElementById("optD").innerText = q.options.D;

    correctAnswer = q.answer;
    document.getElementById("result").innerText = "";

    clearSelection();
}

// SUBMIT ANSWER
function submitAnswer() {
    const options = document.getElementsByName("option");
    let selected = "";
    for (let opt of options) {
        if (opt.checked) {
            selected = opt.value;
            break;
        }
    }

    if (selected === "") {
        alert("Please select an option");
        return;
    }

    if (selected === correctAnswer) {
        score++;
        document.getElementById("result").innerText = "✅ Correct!";
        document.getElementById("result").style.color = "green";
    } else {
        document.getElementById("result").innerText =
            `❌ Wrong! Correct answer: ${correctAnswer}`;
        document.getElementById("result").style.color = "red";
    }

    document.getElementById("score").innerText = `Score: ${score}`;
}

// NEXT QUESTION
function nextQuestion() {
    currentIndex++;
    if (currentIndex >= questions.length) {
        document.getElementById("questionText").innerText =
            `🎉 Test Finished! Final Score: ${score} / ${questions.length}`;
        document.querySelector(".options").style.display = "none";
        document.getElementById("result").innerText = "";

        if (countdown) clearInterval(countdown); // stop timer
        return;
    }
    loadQuestion();
}

// CLEAR RADIO BUTTON SELECTION
function clearSelection() {
    const options = document.getElementsByName("option");
    for (let opt of options) opt.checked = false;
}

// TIMER
function startTimer(seconds) {
    let timeLeft = seconds;
    const timer = document.getElementById("timer");

    countdown = setInterval(function () {
        timer.innerHTML = "Time left: " + timeLeft + " sec";
        timeLeft--;

        if (timeLeft < 0) {
            clearInterval(countdown);
            timer.innerHTML = "⏰ Time's up!";
            // Disable all options & next button
            const opts = document.getElementsByName("option");
            for (let opt of opts) opt.disabled = true;
            document.getElementById("nextBtn").disabled = true;
        }
    }, 1000);
}
