document.addEventListener("DOMContentLoaded", function () {
    let uid = document.body.dataset.uid;
    const generateBtn = document.getElementById("generateBtn");
    const regenerateBtn = document.getElementById("regenerateBtn");
    const evaluateBtn = document.getElementById("evaluateBtn");

    const reportStatus = document.getElementById("reportStatus");
    const loadingSpinner = document.getElementById("loadingSpinner");
    const reportContainer = document.getElementById("reportContainer");
    const reportContent = document.getElementById("reportContent");

    // 获取已生成报告
    async function fetchReport() {
        try {
            const res = await fetch(`/report/${uid}`, {method: "PUT"});
            const data = await res.json();

            if (data.status === "redirect") {
                window.location.href = data.redirect_url;
            }

            if (data.report && data.report.trim() !== "") {
                renderReport(data.report);
            } else {
                reportStatus.style.display = "block";
            }
        } catch (err) {
            console.error("获取报告失败:", err);
        }
    }

    // 渲染报告
    function renderReport(html) {
        reportContent.innerHTML = html;

        // 显示报告区域
        reportStatus.style.display = "none";
        loadingSpinner.style.display = "none";
        reportContainer.style.display = "block";

        // 隐藏“生成”按钮，显示“重新生成”和“评价”
        generateBtn.style.display = "none";
        regenerateBtn.style.display = "inline-block";
        evaluateBtn.style.display = "inline-block";
    }

    // 生成报告
    async function generateReport() {
        reportStatus.style.display = "none";
        reportContainer.style.display = "none";
        regenerateBtn.style.display = "none";
        evaluateBtn.style.display = "none";
        loadingSpinner.style.display = "block";

        try {
            const res = await fetch(`/report/${uid}`, {method: "POST"});
            const data = await res.json();

            if (data.status === "redirect") {
                window.location.href = data.redirect_url;
            }

            if (data.status === "success" && data.report && data.report.trim() !== "") {
                renderReport(data.report);
            } else {
                throw new Error("报告为空");
            }
        } catch (err) {
            loadingSpinner.style.display = "none";
            reportStatus.style.display = "block";
            reportStatus.classList.add("medical-alert-danger");
            reportStatus.innerText = "报告生成失败，请稍后重试。";
        }
    }

    // 按钮绑定事件
    generateBtn.addEventListener("click", generateReport);
    regenerateBtn.addEventListener("click", generateReport);

    // 页面加载时尝试获取报告
    fetchReport();
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