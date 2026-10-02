document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-faq-video]");
  if (!button || !/^[A-Za-z0-9_-]{11}$/.test(button.dataset.faqVideo)) return;
  const frame = document.createElement("iframe");
  frame.src = `https://www.youtube-nocookie.com/embed/${button.dataset.faqVideo}?autoplay=1`;
  frame.title = button.dataset.title;
  frame.allow = "autoplay; encrypted-media; picture-in-picture";
  frame.allowFullscreen = true;
  button.replaceWith(frame);
});
