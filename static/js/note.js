document.addEventListener("DOMContentLoaded", function () {
    let uid = document.body.dataset.uid;
    const generateBtn = document.getElementById("generateBtn");
    const regenerateBtn = document.getElementById("regenerateBtn");
    const evaluateBtn = document.getElementById("evaluateBtn");

    const noteStatus = document.getElementById("noteStatus");
    const loadingSpinner = document.getElementById("loadingSpinner");
    const noteContainer = document.getElementById("noteContainer");
    const noteContent = document.getElementById("noteContent");

    // 获取已生成报告
    async function fetchNote() {
        try {
            const res = await fetch(`/note/${uid}`, {method: "PUT"});
            const data = await res.json();

            if (data.status === "redirect") {
                window.location.href = data.redirect_url;
            }

            if (data.note && data.note.trim() !== "") {
                renderNote(data.note);
            } else {
                noteStatus.style.display = "block";
            }
        } catch (err) {
            console.error("获取病历失败:", err);
        }
    }

    // 渲染报告
    function renderNote(html) {
        noteContent.innerHTML = html;

        // 显示报告区域
        noteStatus.style.display = "none";
        loadingSpinner.style.display = "none";
        noteContainer.style.display = "block";

        // 隐藏“生成”按钮，显示“重新生成”和“评价”
        generateBtn.style.display = "none";
        regenerateBtn.style.display = "inline-block";
        evaluateBtn.style.display = "inline-block";
    }

    // 生成病历
    async function generateNote() {
        noteStatus.style.display = "none";
        noteContainer.style.display = "none";
        regenerateBtn.style.display = "none";
        evaluateBtn.style.display = "none";
        loadingSpinner.style.display = "block";

        try {
            const res = await fetch(`/note/${uid}`, {method: "POST"});
            const data = await res.json();

            if (data.status === "redirect") {
                window.location.href = data.redirect_url;
            }

            if (data.status === "success" && data.note && data.note.trim() !== "") {
                renderNote(data.note);
            } else {
                throw new Error("病历为空");
            }
        } catch (err) {
            loadingSpinner.style.display = "none";
            noteStatus.style.display = "block";
            noteStatus.classList.add("medical-alert-danger");
            noteStatus.innerText = "病历生成失败，请稍后重试。";
        }
    }

    // 按钮绑定事件
    generateBtn.addEventListener("click", generateNote);
    regenerateBtn.addEventListener("click", generateNote);

    // 页面加载时尝试获取报告
    fetchNote();
});

document.getElementById('uidText').addEventListener('click', function () {
    const text = this.innerText || this.textContent;
    const tip = document.getElementById('copyTip');

    function showTip() {
        tip.style.opacity = '1';
        setTimeout(() => {
            tip.style.opacity = '0';
        }, 1500);
    }

    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(() => {
            showTip();
        }, () => {
            fallbackCopy();
        });
    } else {
        fallbackCopy();
    }

    function fallbackCopy() {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        document.body.appendChild(textArea);
        textArea.select();
        try {
            const successful = document.execCommand('copy');
            if (successful) {
                showTip();
            }
        } catch (err) {
        }
        document.body.removeChild(textArea);
    }
});