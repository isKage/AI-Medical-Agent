// 全局变量
let isThinking = false;
let uid = document.body.dataset.uid;

// 自动滚动到底部
function scrollToBottom() {
    const chatBox = document.getElementById("chat-box");
    chatBox.scrollTop = chatBox.scrollHeight;
}

// 添加消息到聊天框
function addMessage(role, content, isThinking = false, count = 0) {
    const chatBox = document.getElementById("chat-box");
    const messageRow = document.createElement("div");
    messageRow.className = `message-row ${role.toLowerCase()}`;

    const avatar = document.createElement("div");
    avatar.className = "avatar";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";

    if (role === "AI" || role === "ai") {
        avatar.innerHTML = '<i class="bi bi-robot fs-5"></i>';
        if (isThinking) {
            bubble.innerHTML = `
                        <span class="thinking-animation" style="width: 48px">
                            <span class="thinking-dots"></span>
                        </span>
                    `;
            messageRow.id = "thinking-message";
        } else {
            // 根据 count 值添加不同的警告提示和样式
            if (count === 1) {
                bubble.innerHTML = '<div style="color: #856404; font-weight: bold; margin-bottom: 8px;">⚠️ 请认真回答问题</div><div>' + content + '</div>';
                bubble.classList.add('warning-yellow');
            } else if (count === 2) {
                bubble.innerHTML = '<div style="color: #721c24; font-weight: bold; margin-bottom: 8px;">⚠️ 否则跳过当前问题</div><div>' + content + '</div>';
                bubble.classList.add('warning-red');
            } else {
                bubble.textContent = content;
            }
        }
    } else {
        avatar.innerHTML = '<i class="bi bi-person fs-5"></i>';
        bubble.textContent = content;
    }

    messageRow.appendChild(avatar);
    messageRow.appendChild(bubble);
    chatBox.appendChild(messageRow);

    scrollToBottom();
    return messageRow;
}

// 移除思考中的消息
function removeThinkingMessage() {
    const thinkingMessage = document.getElementById("thinking-message");
    if (thinkingMessage) {
        thinkingMessage.remove();
    }
}

// 设置发送按钮状态
function setSendButtonState(isLoading) {
    const sendBtn = document.getElementById("send-btn");
    const sendContent = document.getElementById("send-content");
    const messageInput = document.getElementById("message-input");

    if (isLoading) {
        sendBtn.disabled = true;
        messageInput.disabled = true;
        sendContent.innerHTML = `
                    <span class="spinner-border spinner-border-sm me-1" role="status"></span>
                    思考中...
                `;
    } else {
        sendBtn.disabled = false;
        messageInput.disabled = false;
        sendContent.innerHTML = `
                    <i class="bi bi-send me-1"></i>发送
                `;
    }
}

// 显示结束对话弹窗
function showEndChatModal() {
    // 创建弹窗 HTML
    const modalHtml = `
        <div class="modal fade" id="endChatModal" tabindex="-1" aria-labelledby="endChatModalLabel" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="endChatModalLabel">
                            <i class="bi bi-clipboard-check me-2"></i>问诊补充信息
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="关闭"></button>
                    </div>
                    <div class="modal-body">
                        <form id="endChatForm">
                            <div class="mb-3">
                                <label for="additionalInfo" class="form-label">请补充其他相关信息（可选）：</label>
                                <textarea class="form-control" id="additionalInfo" name="addition" rows="4" 
                                    placeholder="例如：既往病史、过敏史、用药史、家族史等其他您认为重要的信息..."></textarea>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                        <button type="button" class="btn btn-primary" onclick="submitEndChat()">
                            <i class="bi bi-check-circle me-1"></i>完成问诊
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;

    // 如果弹窗已存在，先移除
    const existingModal = document.getElementById('endChatModal');
    if (existingModal) {
        existingModal.remove();
    }

    // 添加弹窗到页面
    document.body.insertAdjacentHTML('beforeend', modalHtml);

    // 显示弹窗
    const modal = new bootstrap.Modal(document.getElementById('endChatModal'));
    modal.show();
}

// 提交结束对话信息
async function submitEndChat() {
    const additionalInfo = document.getElementById('additionalInfo').value.trim();
    const modal = bootstrap.Modal.getInstance(document.getElementById('endChatModal'));

    try {
        // 显示加载状态
        const submitBtn = document.querySelector('#endChatModal .btn-primary');
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>处理中...';
        submitBtn.disabled = true;

        // 发送POST请求
        const formData = new FormData();
        formData.append('addition', additionalInfo);

        const response = await fetch(`/chat/addition/${uid}`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.status === 'redirect') {
            // 关闭弹窗并跳转
            modal.hide();
            window.location.href = data.redirect_url;
        } else {
            throw new Error('服务器响应错误');
        }

    } catch (error) {
        console.error('提交失败:', error);
        alert('提交失败，请稍后再试');

        // 恢复按钮状态
        const submitBtn = document.querySelector('#endChatModal .btn-primary');
        submitBtn.innerHTML = '<i class="bi bi-check-circle me-1"></i>完成问诊';
        submitBtn.disabled = false;
    }
}


// 发送消息
async function sendMessage(event) {
    event.preventDefault();

    if (isThinking) {
        return;
    }

    const messageInput = document.getElementById("message-input");
    const message = messageInput.value.trim();

    if (!message) {
        return;
    }

    // 设置思考状态
    isThinking = true;
    setSendButtonState(true);

    // 立即显示用户消息
    addMessage("user", message);

    // 清空输入框
    messageInput.value = "";

    // 显示AI思考中
    addMessage("AI", "", true);

    try {
        // 发送AJAX请求
        const formData = new FormData();
        formData.append('message', message);

        const response = await fetch(`/chat/${uid}`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.status === 'success') {
            // 移除思考中的消息
            removeThinkingMessage();

            // 添加AI回复
            addMessage("AI", data.ai_message.content, false, data.count || 0);
        } else if (data.status === 'redirect') {
            window.location.href = data.redirect_url;
        } else if (data.status === 'endChat') {
            // 后端检测到结束信号，移除思考消息并显示结束弹窗
            removeThinkingMessage();
            showEndChatModal();
        } else {
            throw new Error('服务器响应错误');
        }

    } catch (error) {
        console.error('发送消息失败:', error);
        removeThinkingMessage();
        addMessage("AI", "抱歉，服务器出现了问题，请稍后再试。");
    } finally {
        // 重置状态
        isThinking = false;
        setSendButtonState(false);
        messageInput.focus();
    }
}

// 页面加载完成后的初始化
document.addEventListener('DOMContentLoaded', function () {
    scrollToBottom();
    document.getElementById("message-input").focus();

    // 添加回车发送功能
    document.getElementById("message-input").addEventListener('keypress', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!isThinking) {
                sendMessage(e);
            }
        }
    });
});

// no_sense 自动弹出
document.addEventListener('DOMContentLoaded', function () {
    var modal = new bootstrap.Modal(document.getElementById('noSenseInfo'));
    modal.show();
});

// 监听窗口大小变化，自动滚动到底部
window.addEventListener('resize', scrollToBottom);