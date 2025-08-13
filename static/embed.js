(function () {
	if (window.SuperionChatbotLoaded) return;
	window.SuperionChatbotLoaded = true;

	var host = (function () {
		try { return new URL(document.currentScript.src).origin; } catch (e) { return window.location.origin; }
	})();

	var iframe = document.createElement('iframe');
	iframe.src = host + '/static/widget.html';
	iframe.title = 'Superion Chatbot';
	iframe.style.position = 'fixed';
	iframe.style.width = '360px';
	iframe.style.height = '520px';
	iframe.style.border = '0';
	iframe.style.zIndex = '2147483647';
	iframe.style.bottom = '20px';
	iframe.style.right = '20px';
	iframe.style.boxShadow = '0 8px 28px rgba(0,0,0,0.2)';
	iframe.style.borderRadius = '16px';
	iframe.style.overflow = 'hidden';
	iframe.style.display = 'none';

	var toggle = document.createElement('div');
	toggle.setAttribute('aria-label', 'Open chat');
	toggle.setAttribute('role', 'button');
	toggle.tabIndex = 0;
	toggle.style.position = 'fixed';
	toggle.style.bottom = '20px';
	toggle.style.right = '20px';
	toggle.style.width = '56px';
	toggle.style.height = '56px';
	toggle.style.borderRadius = '50%';
	toggle.style.background = '#0f62fe';
	toggle.style.boxShadow = '0 8px 28px rgba(0,0,0,0.2)';
	toggle.style.cursor = 'pointer';
	toggle.style.zIndex = '2147483646';
	toggle.style.display = 'flex';
	toggle.style.alignItems = 'center';
	toggle.style.justifyContent = 'center';
	toggle.style.color = '#fff';
	toggle.style.fontFamily = 'system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Noto Sans, Helvetica, Arial, Apple Color Emoji, Segoe UI Emoji';
	toggle.style.fontSize = '24px';
	toggle.textContent = '✳';

	function openChat() {
		iframe.style.display = 'block';
		// Keep toggle visible; iframe has higher z-index and will appear above
		try { iframe.contentWindow && iframe.contentWindow.focus && iframe.contentWindow.focus(); } catch (e) {}
	}

	function closeChat() {
		iframe.style.display = 'none';
		toggle.style.display = 'flex';
		toggle.focus();
	}

	toggle.addEventListener('click', openChat);
	toggle.addEventListener('keydown', function (e) {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			openChat();
		}
	});

	document.body.appendChild(iframe);
	document.body.appendChild(toggle);

	window.addEventListener('message', function (event) {
		if (!event || !event.data) return;
		if (event.data === 'superion:close') closeChat();
		if (event.data === 'superion:open') openChat();
	});
})();
