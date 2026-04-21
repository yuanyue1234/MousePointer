const slides = Array.from(document.querySelectorAll(".slide"));
const dotsRoot = document.getElementById("carouselDots");
const prevBtn = document.getElementById("prevBtn");
const nextBtn = document.getElementById("nextBtn");

let activeIndex = 0;
let timerId = null;

function renderDots() {
  slides.forEach((_, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "carousel-dot";
    button.setAttribute("aria-label", `查看第 ${index + 1} 张截图`);
    button.addEventListener("click", () => setActive(index, true));
    dotsRoot.appendChild(button);
  });
}

function setActive(index, resetTimer = false) {
  activeIndex = (index + slides.length) % slides.length;
  slides.forEach((slide, slideIndex) => {
    slide.classList.toggle("active", slideIndex === activeIndex);
  });
  Array.from(dotsRoot.children).forEach((dot, dotIndex) => {
    dot.classList.toggle("active", dotIndex === activeIndex);
  });
  if (resetTimer) {
    startAutoPlay();
  }
}

function startAutoPlay() {
  window.clearInterval(timerId);
  timerId = window.setInterval(() => {
    setActive(activeIndex + 1);
  }, 4200);
}

prevBtn.addEventListener("click", () => setActive(activeIndex - 1, true));
nextBtn.addEventListener("click", () => setActive(activeIndex + 1, true));

renderDots();
setActive(0);
startAutoPlay();
