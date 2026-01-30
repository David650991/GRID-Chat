import { createPopup } from 'https://unpkg.com/@picmo/popup-picker@latest/dist/index.js?module';

const socket = io();
let room = null;
let myUsername = null;
let lastMessageUser = null;

// Initialize from data attributes
document.addEventListener('DOMContentLoaded', () => {
    const chatContainer = document.getElementById('chat-config');
    if (chatContainer) {
        room = chatContainer.dataset.room;
        myUsername = chatContainer.dataset.username;

        initSocket();
        initUI();
    }
});

function initSocket() {
    socket.on('connect', () => socket.emit('join', { room: room }));

    socket.on('message', (data) => appendMessage(data));

    socket.on('historial_previo', (msgs) => {
        document.getElementById('chat-window').innerHTML = '';
        lastMessageUser = null;
        msgs.forEach(appendMessage);
        scrollToBottom();
    });

    socket.on('update_users', (users) => {
        const list = document.getElementById('room-users-list');
        list.innerHTML = '';
        users.forEach(u => {
            list.innerHTML += `
                <div class="user-item">
                    <img src="${u.avatar}" class="user-item-avatar">
                    <div class="user-item-info">
                        <span class="user-item-name">${u.username}</span>
                    </div>
                </div>`;
        });
    });
}

function initUI() {
    // Auto-expand textarea
    const tx = document.getElementsByTagName("textarea");
    for (let i = 0; i < tx.length; i++) {
        tx[i].setAttribute("style", "height:" + (tx[i].scrollHeight) + "px;overflow-y:hidden;");
        tx[i].addEventListener("input", function() {
            this.style.height = "auto";
            this.style.height = (this.scrollHeight) + "px";
        }, false);
    }

    // Input Enter key
    document.getElementById('message_input').addEventListener('keydown', (e) => {
        if(e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Mobile Menu
    const menuBtn = document.getElementById('mobileMenuBtn');
    if(menuBtn) {
        menuBtn.addEventListener('click', () => {
            document.getElementById('mainSidebar').classList.toggle('visible');
        });
    }

    // Emoji Picker
    const trigger = document.querySelector('#emoji-trigger');
    const input = document.querySelector('#message_input');
    try {
        const picker = createPopup({ theme: 'dark' }, { referenceElement: trigger, triggerElement: trigger, position: 'top-start' });
        trigger.addEventListener('click', () => picker.toggle());
        picker.addEventListener('emoji:select', (selection) => {
            input.value += selection.emoji;
            input.focus();
        });
    } catch(e) {}
}

// Global functions exposed for HTML onlick (though preferred addEventListener)
window.sendMessage = function() {
    const input = document.getElementById('message_input');
    const val = input.value.trim();
    if(val) {
        socket.emit('message', { msg: val, room: room });
        input.value = '';
        input.style.height = 'auto';
        input.focus();
    }
};

window.switchTab = function(tab) {
    document.querySelectorAll('.nav-tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.list-viewport').forEach(c => c.classList.add('hidden'));
    document.querySelectorAll('.list-viewport').forEach(c => c.classList.remove('active'));

    // Find the clicked button by iterating or event target check is complex in global scope
    // Simplified: Just set active class to event target if passed correctly or find by text
    // Better: Rely on event bubbling in production, but for now:
    const btn = Array.from(document.querySelectorAll('.nav-tab')).find(b => b.getAttribute('onclick').includes(tab));
    if(btn) btn.classList.add('active');

    const el = document.getElementById(`tab-${tab}`);
    el.classList.remove('hidden');
    el.classList.add('active');
};

window.openProfileModal = () => document.getElementById('profileModal').classList.remove('hidden');
window.closeProfileModal = () => document.getElementById('profileModal').classList.add('hidden');

// --- Message Logic ---

function escapeHtml(text) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return text.replace(/[&<>"']/g, function(m) { return map[m]; });
}

function formatMessage(text) {
    let safeText = escapeHtml(text);
    return safeText.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
}

function appendMessage(data) {
    const win = document.getElementById('chat-window');
    const sameUser = lastMessageUser === data.username;

    if (sameUser) {
        const lastGroup = win.lastElementChild;
        if (lastGroup && lastGroup.classList.contains('msg-group')) {
            const body = lastGroup.querySelector('.msg-body');
            const bubble = document.createElement('div');
            bubble.className = 'msg-bubble';
            bubble.innerHTML = formatMessage(data.msg);
            body.appendChild(bubble);
            lastMessageUser = data.username;
            scrollToBottom();
            return;
        }
    }

    const group = document.createElement('div');
    group.className = 'msg-group';
    group.innerHTML = `
        <img src="${data.avatar || 'https://api.dicebear.com/7.x/identicon/svg?seed='+data.username}" class="msg-avatar">
        <div class="msg-body">
            <div class="msg-header">
                <span class="msg-username">${data.username}</span>
                <span class="msg-timestamp">${data.hora || ''}</span>
            </div>
            <div class="msg-bubble" id="msg-${data.id}">${formatMessage(data.msg)}</div>
        </div>
        <div class="msg-actions">
            <button class="tool-btn" onclick="triggerCtx(event, ${data.id}, '${data.username}', '${data.msg.replace(/'/g, "\\'")}')">⋮</button>
        </div>
    `;

    group.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        showContextMenu(e, data);
    });

    win.appendChild(group);
    lastMessageUser = data.username;
    scrollToBottom();
}

function scrollToBottom() {
    const win = document.getElementById('chat-window');
    win.scrollTop = win.scrollHeight;
}

// Context Menu
window.triggerCtx = function(e, id, username, msg) {
    e.stopPropagation(); // prevent bubbling
    showContextMenu(e, {id, username, msg});
};

function showContextMenu(e, data) {
    const menu = document.getElementById('contextMenu');
    // Adjust position if click is from button (e.target) or right click (e.pageX)
    let x = e.pageX;
    let y = e.pageY;

    // If e is mostly an element click (triggerCtx)
    if(e.clientX) {
        x = e.pageX; y = e.pageY;
    }

    menu.style.top = y + 'px';
    menu.style.left = x + 'px';
    menu.classList.remove('hidden');
    window.currentMsg = data;

    const canDelete = (data.username === myUsername);
    const delOpt = document.getElementById('deleteOption');
    if(delOpt) delOpt.style.display = canDelete ? 'block' : 'none';

    setTimeout(() => {
        document.addEventListener('click', () => menu.classList.add('hidden'), { once: true });
    }, 10);
}

window.replyMessage = () => {
    const input = document.getElementById('message_input');
    input.value = `> @${window.currentMsg.username}: ${window.currentMsg.msg}\n`;
    input.focus();
};
window.copyMessage = () => navigator.clipboard.writeText(window.currentMsg.msg);
window.deleteMessageContext = () => socket.emit('borrar_mensaje', { id: window.currentMsg.id, room: room });

// Profile Logic
window.updateEditPreview = () => document.getElementById('editAvatarPreview').src = document.getElementById('editAvatarUrl').value;
window.randomAvatar = () => {
    const rnd = Math.random().toString(36).substring(7);
    document.getElementById('editAvatarUrl').value = `https://api.dicebear.com/7.x/avataaars/svg?seed=${rnd}`;
    window.updateEditPreview();
};
window.saveProfile = async () => {
    const data = {
        avatar_url: document.getElementById('editAvatarUrl').value,
        bio: document.getElementById('editBio').value,
        email: document.getElementById('editEmail').value
    };
    await fetch('/api/update_profile', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
    location.reload();
};
