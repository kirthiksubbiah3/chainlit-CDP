// This JS file is used to hide the New chat dialog

(function () {
  const observer = new MutationObserver(() => {
    const dialog = document.querySelector('#new-chat-dialog');
    if (dialog && dialog.getAttribute('data-state') === 'open') {
      dialog.style.display = 'none';
      const confirmBtn = dialog.querySelector('#confirm');
      if (confirmBtn) {
        setTimeout(() => confirmBtn.click(), 0);
      }
    }
  });

  observer.observe(document.body, { childList: true, subtree: true });
})();
