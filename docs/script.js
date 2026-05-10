const slides = Array.from(document.querySelectorAll(".slide"));
const dotsRoot = document.getElementById("carouselDots");
const prevBtn = document.getElementById("prevBtn");
const nextBtn = document.getElementById("nextBtn");
const langButtons = Array.from(document.querySelectorAll(".lang-btn"));
const navLinks = Array.from(document.querySelectorAll(".nav a"));
const pageSections = [
  document.querySelector(".hero"),
  document.querySelector("#features"),
  document.querySelector("#workflow")
].filter(Boolean);
const wechatButton = document.getElementById("wechatButton");
const wechatPanel = document.getElementById("wechatPanel");
const referencesSection = document.getElementById("references");

let activeIndex = 0;
let timerId = null;
let currentLang = "zh";
let sectionScrollLocked = false;

const translations = {
  zh: {
    brand: "鼠标指针配置管理器",
    navFeatures: "功能特性",
    navWorkflow: "快速上手",
    download: "下载软件",
    wechatButton: "微信公众号",
    reservedSlot: "预留按钮位",
    iconLabel: "软件图标",
    iconTitle: "鼠标指针配置管理器",
    iconText: "让新手小白也能用，让鼠标指针制作者能方便编辑和生成。",
    downloadNow: "立即下载",
    resourceLibrary: "在线资源库",
    githubRepo: "GitHub 项目仓库",
    eyebrow: "Windows 鼠标指针方案图形化工具",
    heroTitle: "让方案导入、预览、应用和打包都变得更直观。",
    heroText:
      "为新手用户准备的轻量化桌面工具，也为鼠标指针制作者保留足够清晰的编辑与调试体验。你可以直接导入资源包、拖入文件、实时预览动态指针，再一键生成安装程序。",
    point1: "支持 `.cur`、`.ani`、图片、压缩包、文件夹与 `exe` 导入",
    point2: "支持动态预览、GIF 截图导出与后台常驻",
    point3: "支持新建、重命名、导入、应用与安装包生成",
    statusText: "实时预览 · 方案管理 · 资源导入",
    caption1: "方案编辑与预览联动",
    caption2: "资源库与导入流程",
    caption3: "设置、下载与系统集成",
    workflowEyebrow: "快速上手",
    workflowTitle: "从下载到应用，只需要四步。",
    step1Title: "下载安装",
    step1Text: "从 GitHub Releases 下载绿色版程序，开箱可用。",
    step2Title: "拖入资源",
    step2Text: "把指针文件、资源包或文件夹直接拖进应用，程序自动解析。",
    step3Title: "预览与调整",
    step3Text: "在方案页分配各个状态，右侧实时查看显示效果。",
    step4Title: "应用或打包",
    step4Text: "一键写入系统鼠标方案，或直接生成安装程序交付使用。",
    featureEyebrow: "功能特性",
    featureTitle: "围绕编辑效率与可视化体验设计。",
    f1Title: "方案管理",
    f1Text: "新建、重命名、删除、导入和自动保存方案，避免重复整理资源。",
    f2Title: "自由导入",
    f2Text: "支持 `.cur`、`.ani`、图片、`.zip`、`.rar`、`.7z`、`.exe` 和文件夹且支持多份同时导入。",
    f3Title: "鼠标焦点",
    f3Text: "静态与动态鼠标指针都能直接查看和自定义鼠标焦点，支持快速编辑鼠标焦点。",
    f4Title: "大小无感调节",
    f4Text: "实时无感，分段调节鼠标大小。",
    f5Title: "截图导出",
    f5Text: "可导出方案预览图，动态指针保存为 GIF，便于分享和留档。",
    f6Title: "按需切换",
    f6Text: "支持时间切换方案、日期切换方案、定时切换方案、大小写切换方案。",
    refEyebrow: "参考",
    refTitle: "实现与灵感来源。",
    r1: "GitHub 项目仓库",
    r2: "InputTip 中英文切换思路",
    r3: "InputTip 扩展鼠标指针资源",
    r4: "PyQt-Fluent-Widgets 界面风格参考",
    r5: "像素指针指南文章",
    refActionProject: "查看项目",
    refActionReference: "查看参考",
    refActionResource: "查看资源",
    refActionFramework: "查看框架",
    refActionArticle: "查看文章"
  },
  en: {
    brand: "Mouse Pointer Manager",
    navFeatures: "Features",
    navWorkflow: "Quick Start",
    download: "Download",
    wechatButton: "WeChat",
    reservedSlot: "Reserved Slot",
    iconLabel: "App Icon",
    iconTitle: "Mouse Pointer Manager",
    iconText: "Built for beginners while still making editing and packaging easy for cursor creators.",
    downloadNow: "Download Now",
    resourceLibrary: "Resource Library",
    githubRepo: "GitHub Repository",
    eyebrow: "Windows Cursor Scheme Visual Tool",
    heroTitle: "Make importing, previewing, applying, and packaging cursor schemes easier to understand.",
    heroText:
      "Built for beginners, while still keeping a clear editing and debugging workflow for cursor creators. Import resource packs, drag files in, preview animated cursors, and generate an installer in one flow.",
    point1: "Supports `.cur`, `.ani`, images, archives, folders, and `exe` imports",
    point2: "Supports animated preview, GIF export, and background mode",
    point3: "Supports creating, renaming, importing, applying, and packaging schemes",
    statusText: "Live Preview · Scheme Management · Resource Import",
    caption1: "Scheme editing and preview linkage",
    caption2: "Resource library and import flow",
    caption3: "Settings, downloads, and system integration",
    workflowEyebrow: "Quick Start",
    workflowTitle: "From download to apply, it takes only four steps.",
    step1Title: "Download",
    step1Text: "Download the portable build from GitHub Releases and start immediately.",
    step2Title: "Import Resources",
    step2Text: "Drag cursor files, packages, or folders into the app and let it parse them automatically.",
    step3Title: "Preview and Adjust",
    step3Text: "Assign resources on the scheme page and check the live preview on the right.",
    step4Title: "Apply or Package",
    step4Text: "Write the scheme into Windows or generate an installer for distribution.",
    featureEyebrow: "Features",
    featureTitle: "Designed around editing efficiency and visual feedback.",
    f1Title: "Scheme Management",
    f1Text: "Create, rename, delete, import, and auto-save schemes without repeated file sorting.",
    f2Title: "Flexible Import",
    f2Text: "Supports `.cur`, `.ani`, images, `.zip`, `.rar`, `.7z`, `.exe`, folders, and multiple items at once.",
    f3Title: "Cursor Hotspot",
    f3Text: "Preview static and animated cursors and quickly customize cursor hotspots.",
    f4Title: "Smooth Size Control",
    f4Text: "Adjust cursor size in real time with segmented, low-friction steps.",
    f5Title: "Screenshot Export",
    f5Text: "Export preview images, and keep animation frames in GIF format when needed.",
    f6Title: "Switch on Demand",
    f6Text: "Supports time-based, date-based, scheduled, and Caps Lock scheme switching.",
    refEyebrow: "References",
    refTitle: "Implementation and inspiration sources.",
    r1: "GitHub Project Repository",
    r2: "InputTip Chinese/English switching idea",
    r3: "InputTip extended cursor resources",
    r4: "PyQt-Fluent-Widgets UI reference",
    r5: "Pixel cursor guide article",
    refActionProject: "Open Project",
    refActionReference: "View Reference",
    refActionResource: "View Resource",
    refActionFramework: "View Framework",
    refActionArticle: "Read Article"
  }
};

function renderDots() {
  if (!dotsRoot) return;
  dotsRoot.innerHTML = "";
  slides.forEach((_, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "carousel-dot";
    button.setAttribute("aria-label", `View screenshot ${index + 1}`);
    button.addEventListener("click", () => setActive(index, true));
    dotsRoot.appendChild(button);
  });
}

function setActive(index, resetTimer = false) {
  if (!slides.length) return;
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

function applyLanguage(lang) {
  currentLang = lang;
  const dict = translations[lang];
  document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    const key = node.getAttribute("data-i18n");
    if (dict[key]) {
      node.textContent = dict[key];
    }
  });
  langButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.lang === lang);
  });
}

function updateActiveNav() {
  let matchedId = "";

  if (pageSections.length) {
    const currentSection = pageSections[getCurrentSectionIndex()];
    matchedId = currentSection ? currentSection.id : "";
  }

  navLinks.forEach((link) => {
    const href = link.getAttribute("href");
    link.classList.toggle("active", href === `#${matchedId}`);
  });
}

function getCurrentSectionIndex() {
  const anchorY = window.scrollY + window.innerHeight * 0.35;
  let bestIndex = 0;
  let bestDistance = Number.POSITIVE_INFINITY;

  pageSections.forEach((section, index) => {
    const sectionCenter = section.offsetTop + section.offsetHeight / 2;
    const distance = Math.abs(sectionCenter - anchorY);
    if (distance < bestDistance) {
      bestDistance = distance;
      bestIndex = index;
    }
  });

  return bestIndex;
}

function scrollToSection(index) {
  if (!pageSections.length) return;
  const safeIndex = Math.max(0, Math.min(index, pageSections.length - 1));
  const top = Math.max(0, pageSections[safeIndex].offsetTop - 86);
  window.scrollTo({ top, behavior: "smooth" });
  sectionScrollLocked = true;
  window.setTimeout(() => {
    sectionScrollLocked = false;
    updateActiveNav();
  }, 720);
}

function handleSectionWheel(event) {
  if (window.innerWidth <= 760) return;
  if (sectionScrollLocked) {
    event.preventDefault();
    return;
  }
  if (Math.abs(event.deltaY) < 12) return;

  const currentSectionIndex = getCurrentSectionIndex();
  const direction = event.deltaY > 0 ? 1 : -1;
  const nextIndex = Math.max(0, Math.min(currentSectionIndex + direction, pageSections.length - 1));

  if (nextIndex === currentSectionIndex) return;

  event.preventDefault();
  scrollToSection(nextIndex);
}

if (prevBtn) {
  prevBtn.addEventListener("click", () => setActive(activeIndex - 1, true));
}

if (nextBtn) {
  nextBtn.addEventListener("click", () => setActive(activeIndex + 1, true));
}

langButtons.forEach((button) => {
  button.addEventListener("click", () => applyLanguage(button.dataset.lang));
});

if (wechatButton && wechatPanel) {
  wechatButton.addEventListener("click", () => {
    wechatPanel.hidden = !wechatPanel.hidden;
  });
}

navLinks.forEach((link) => {
  link.addEventListener("click", () => {
    const target = document.querySelector(link.getAttribute("href"));
    if (!target) return;
    sectionScrollLocked = true;
    window.setTimeout(() => {
      sectionScrollLocked = false;
      updateActiveNav();
    }, 720);
  });
});

renderDots();
setActive(0);
startAutoPlay();
applyLanguage(currentLang);
updateActiveNav();
window.addEventListener("scroll", updateActiveNav, { passive: true });
window.addEventListener("wheel", handleSectionWheel, { passive: false });
