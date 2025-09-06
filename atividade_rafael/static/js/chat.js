document.addEventListener('DOMContentLoaded', () => {
    const socket = io();

    // Referências aos elementos do DOM
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const messagesBox = document.getElementById('messages-box');
    const userList = document.getElementById('user-list');
    const username = document.querySelector('.chat-header strong').textContent;
    const emojiBtn = document.getElementById('emoji-btn');
    const emojiPicker = document.querySelector('emoji-picker');
    const photoInput = document.getElementById('photo-input');

    // --- LÓGICA DE EMOJIS ---
    emojiBtn.addEventListener('click', () => {
        emojiPicker.style.display = emojiPicker.style.display === 'none' ? 'block' : 'none';
    });

    emojiPicker.addEventListener('emoji-click', event => {
        messageInput.value += event.detail.unicode;
        emojiPicker.style.display = 'none';
        messageInput.focus();
    });

    // --- LÓGICA DE UPLOAD DE FOTOS ---
    photoInput.addEventListener('change', () => {
        const file = photoInput.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('photo', file);

        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(`Erro no upload: ${data.error}`);
            }
        })
        .catch(error => {
            console.error('Erro no upload:', error);
            alert('Ocorreu um erro ao enviar o arquivo.');
        });
        
        // Limpa o input para poder selecionar o mesmo arquivo novamente
        photoInput.value = '';
    });

    // --- LÓGICA DE MENSAGENS (Socket.IO) ---
    socket.emit('join', { room: 'geral' });

    const sendMessage = () => {
        const message = messageInput.value.trim();
        if (message) {
            socket.emit('send_message', { room: 'geral', msg: message });
            messageInput.value = '';
            messageInput.focus();
        }
    };

    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    // ALTERADO: Agora lida com diferentes tipos de mensagem (texto e imagem)
    const addMessage = (data) => {
        const messageDiv = document.createElement('div');
        const messageType = (data.user === username) ? 'mine' : 'other';
        messageDiv.classList.add('message', messageType);

        const userSpan = document.createElement('span');
        userSpan.classList.add('user');
        userSpan.textContent = data.user;
        messageDiv.appendChild(userSpan);
        
        // Verifica se é uma mensagem de texto ou imagem
        if (data.type === 'image') {
            const img = document.createElement('img');
            img.src = data.url;
            img.classList.add('chat-image');
            messageDiv.appendChild(img);
        } else { // tipo 'text'
            messageDiv.append(data.msg);
        }
        
        messagesBox.appendChild(messageDiv);
        messagesBox.scrollTop = messagesBox.scrollHeight;
    };

    const addStatusMessage = (data) => {
        const statusDiv = document.createElement('div');
        statusDiv.classList.add('message', 'status');
        statusDiv.textContent = data.msg;
        messagesBox.appendChild(statusDiv);
        messagesBox.scrollTop = messagesBox.scrollHeight;
    };

    const updateUserPanel = (users) => {
        userList.innerHTML = '';
        users.forEach(user => {
            const li = document.createElement('li');
            li.className = `user-status-${user.status}`;
            li.textContent = user.name;
            userList.appendChild(li);
        });
    };

    socket.on('receive_message', (data) => addMessage(data));
    socket.on('status', (data) => addStatusMessage(data));
    socket.on('update_user_list', (users) => updateUserPanel(users));
});