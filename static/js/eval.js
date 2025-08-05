document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("eval-form");

    if (form) {
        form.addEventListener("submit", async function (event) {
            event.preventDefault();

            const formData = new FormData(form);
            const mode = form.dataset.mode;
            const uid = form.dataset.uid;

            const res = await fetch(`/eval/${mode}/${uid}`, {
                method: "POST",
                body: formData
            });
            const result = await res.json();

            if (result.status === "success" || result.status === "redirect") {
                window.location.href = result.redirect_url;
            } else {
                alert("提交失败");
            }
        });
    }
});
