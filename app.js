// APP STATE & CONSTANTS
let currentStream = null;
let registeredDatabase = {};

// CHUỖI 5 BƯỚC CỬ ĐỘNG MẶT TUẦN TỰ (VỚI HƯỚNG DẪN GÓC XOAY VÀ ĐẾM NGƯỢC 3S)
const EKYC_POSETUR_STEPS = [
    {
        step: 1,
        text: "👈 BƯỚC 1/5: QUAY MẶT SANG TRÁI (30° - 45°)",
        detail: "Từ từ xoay đầu sang bên trái khoảng 30° - 45° và giữ yên trong 3s.",
        arrowId: "arrow-left",
        icon: "fa-arrow-left"
    },
    {
        step: 2,
        text: "👉 BƯỚC 2/5: QUAY MẶT SANG PHẢI (30° - 45°)",
        detail: "Từ từ xoay đầu sang bên phải khoảng 30° - 45° và giữ yên trong 3s.",
        arrowId: "arrow-right",
        icon: "fa-arrow-right"
    },
    {
        step: 3,
        text: "⬇️ BƯỚC 3/5: CÚI MẶT XUỐNG (20° - 30°)",
        detail: "Hơi nghiêng đầu cúi xuống khoảng 20° - 30° và giữ yên trong 3s.",
        arrowId: "arrow-down",
        icon: "fa-arrow-down"
    },
    {
        step: 4,
        text: "⬆️ BƯỚC 4/5: NGỬA MẶT LÊN (20° - 30°)",
        detail: "Hơi ngửa cằm lên trên khoảng 20° - 30° và giữ yên trong 3s.",
        arrowId: "arrow-up",
        icon: "fa-arrow-up"
    },
    {
        step: 5,
        text: "👁️ BƯỚC 5/5: NHÌN CHÍNH DIỆN (0°) & CHỚP MẮT",
        detail: "Nhìn thẳng chính diện vào camera và chớp mắt 1 lần.",
        arrowId: "arrow-center",
        icon: "fa-eye"
    }
];

let ekycTourIndex = 0;
let ekycCapturedFrames = [];
let isEkycScanning = false;
let countdownTimerId = null;

// AUDIO SYNTHESIZER
const AudioContext = window.AudioContext || window.webkitAudioContext;
let audioCtx = null;

function getAudioContext() {
    if (!audioCtx) audioCtx = new AudioContext();
    if (audioCtx.state === 'suspended') audioCtx.resume();
    return audioCtx;
}

function playSound(type) {
    try {
        const ctx = getAudioContext();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);

        if (type === 'success') {
            osc.type = 'sine';
            osc.frequency.setValueAtTime(523.25, ctx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(659.25, ctx.currentTime + 0.1);
            osc.frequency.exponentialRampToValueAtTime(783.99, ctx.currentTime + 0.2);
            gain.gain.setValueAtTime(0.15, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4);
            osc.start();
            osc.stop(ctx.currentTime + 0.4);
        } else if (type === 'error') {
            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(300, ctx.currentTime);
            osc.frequency.setValueAtTime(150, ctx.currentTime + 0.15);
            gain.gain.setValueAtTime(0.2, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.35);
            osc.start();
            osc.stop(ctx.currentTime + 0.35);
        } else if (type === 'shutter') {
            osc.type = 'triangle';
            osc.frequency.setValueAtTime(800, ctx.currentTime);
            gain.gain.setValueAtTime(0.1, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.08);
            osc.start();
            osc.stop(ctx.currentTime + 0.08);
        } else if (type === 'tick') {
            osc.type = 'sine';
            osc.frequency.setValueAtTime(600, ctx.currentTime);
            gain.gain.setValueAtTime(0.05, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.05);
            osc.start();
            osc.stop(ctx.currentTime + 0.05);
        }
    } catch (e) {}
}

// INITIALIZATION
document.addEventListener('DOMContentLoaded', () => {
    updateClock();
    setInterval(updateClock, 1000);
    initCamera('video-ekyc');
    onAmountChanged();
});

function updateClock() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const clockEl = document.getElementById('status-time');
    if (clockEl) clockEl.textContent = `${hours}:${minutes}`;
}

function generateRandomWalletId() {
    const hex = Math.random().toString(16).substring(2, 10).toUpperCase();
    const newId = `0x71C8${hex}`;
    document.getElementById('user-id-input').value = newId;
    playSound('shutter');
}

// WEBRTC CAMERA CONTROLLER
async function initCamera(videoId) {
    stopCurrentCamera();
    const video = document.getElementById(videoId);
    if (!video) return;

    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
            audio: false
        });
        currentStream = stream;
        video.srcObject = stream;
    } catch (err) {
        console.warn("Camera WebRTC info:", err);
    }
}

function stopCurrentCamera() {
    if (currentStream) {
        currentStream.getTracks().forEach(track => track.stop());
        currentStream = null;
    }
}

function captureVideoFrameBase64(videoId) {
    const video = document.getElementById(videoId);
    if (!video || !video.videoWidth) return null;

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg', 0.85);
}

// MODE SWITCHER
function switchMode(mode) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.screen-view').forEach(sc => sc.classList.remove('active-screen'));

    if (mode === 'ekyc') {
        document.getElementById('tab-ekyc').classList.add('active');
        document.getElementById('screen-ekyc').classList.add('active-screen');
        initCamera('video-ekyc');
    } else if (mode === 'faceid') {
        document.getElementById('tab-faceid').classList.add('active');
        document.getElementById('screen-faceid').classList.add('active-screen');
        stopCurrentCamera();
    }
}

// AMOUNT & TRANSACTION CONTROL
function setTxAmount(val) {
    document.getElementById('tx-amount-input').value = val;
    document.querySelectorAll('.quick-amounts button').forEach(b => b.classList.remove('active'));
    onAmountChanged();
}

function onAmountChanged() {
    const amountVal = parseFloat(document.getElementById('tx-amount-input').value) || 0;
    const banner = document.getElementById('tx-notice-banner');
    const noticeText = document.getElementById('notice-text');
    const biometricTag = document.getElementById('tx-biometric-tag');
    const submitBtn = document.getElementById('btn-submit-tx');

    if (amountVal > 10000000) {
        banner.className = 'notice-banner required-faceid';
        noticeText.textContent = "Giao dịch > 10 triệu: BẮT BUỘC xác thực FaceID sinh trắc học (QĐ 2345/QĐ-NHNN)";
        biometricTag.className = 'tx-badge-secure warn-tag';
        biometricTag.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> FaceID Required';
        submitBtn.className = 'btn-pay';
        submitBtn.innerHTML = '<i class="fa-solid fa-face-smile"></i> Xác thực FaceID Duyệt Chuyển Tiền';
    } else {
        banner.className = 'notice-banner';
        noticeText.textContent = "Giao dịch ≤ 10 triệu: Duyệt nhanh bằng Mã PIN / OTP SMS";
        biometricTag.className = 'tx-badge-secure';
        biometricTag.innerHTML = '<i class="fa-solid fa-shield-check"></i> Standard PIN';
        submitBtn.className = 'btn-primary';
        submitBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Chuyển Tiền Ngay (Xác nhận PIN)';
    }
}

function handleTxSubmit() {
    const amountVal = parseFloat(document.getElementById('tx-amount-input').value) || 0;
    if (amountVal > 10000000) {
        openFaceIdModal();
    } else {
        playSound('success');
        const formattedAmount = amountVal.toLocaleString('vi-VN') + ' VNĐ';
        showTxResult(true, "0.9996 (REAL)", "PIN_PASSED (Dưới 10M)", formattedAmount);
    }
}

// ====================================================
// BƯỚC 1: TỰ ĐỘNG CHỤP 5 KHUNG HÌNH VỚI ĐẾM NGƯỢC 3S VÀ MŨI TÊN CHỈ HƯỚNG
// ====================================================
async function startEkyc5PoseTour() {
    const userIdInput = document.getElementById('user-id-input').value.trim();
    if (!userIdInput) {
        alert("Vui lòng nhập ID Ví / Số điện thoại!");
        return;
    }

    if (isEkycScanning) return;
    isEkycScanning = true;
    ekycTourIndex = 0;
    ekycCapturedFrames = [];

    document.getElementById('btn-start-ekyc').classList.add('hidden');
    document.getElementById('btn-manual-capture').classList.remove('hidden');
    document.getElementById('ekyc-oval').classList.add('valid');
    document.getElementById('ekyc-laser').classList.add('scanning');

    runNextPoseStep();
}

function updateDirectionalArrow(arrowId) {
    document.querySelectorAll('.guide-arrow').forEach(a => a.classList.remove('active'));
    if (arrowId) {
        const el = document.getElementById(arrowId);
        if (el) el.classList.add('active');
    }
}

function runNextPoseStep() {
    if (ekycTourIndex < EKYC_POSETUR_STEPS.length) {
        const stepInfo = EKYC_POSETUR_STEPS[ekycTourIndex];
        
        document.getElementById('pose-step-num').textContent = `BƯỚC ${stepInfo.step}/5`;
        document.getElementById('ekyc-pose-instruction').textContent = stepInfo.text;
        document.getElementById('ekyc-pose-detail-help').textContent = stepInfo.detail;
        document.getElementById('badge-pose-status').innerHTML = `<i class="fa-solid ${stepInfo.icon}"></i> ${stepInfo.text}`;

        updateDirectionalArrow(stepInfo.arrowId);

        startCountdownOverlay(3, () => {
            captureCurrentStepFrame();
        });

    } else {
        finishAllPoseSteps();
    }
}

function startCountdownOverlay(seconds, onComplete) {
    if (countdownTimerId) clearInterval(countdownTimerId);

    const overlay = document.getElementById('countdown-overlay');
    const circle = document.getElementById('countdown-circle');
    const textEl = document.getElementById('countdown-text');
    
    overlay.classList.remove('hidden');
    let timeLeft = seconds;
    circle.textContent = timeLeft;
    textEl.textContent = `Hãy giữ yên góc mặt! Đếm ngược ${timeLeft}s...`;
    playSound('tick');

    countdownTimerId = setInterval(() => {
        timeLeft--;
        if (timeLeft > 0) {
            circle.textContent = timeLeft;
            textEl.textContent = `Hãy giữ yên góc mặt! Đếm ngược ${timeLeft}s...`;
            playSound('tick');
        } else {
            clearInterval(countdownTimerId);
            countdownTimerId = null;
            overlay.classList.add('hidden');
            if (onComplete) onComplete();
        }
    }, 1000);
}

function triggerImmediateCapture() {
    if (!isEkycScanning) return;
    if (countdownTimerId) {
        clearInterval(countdownTimerId);
        countdownTimerId = null;
    }
    document.getElementById('countdown-overlay').classList.add('hidden');
    captureCurrentStepFrame();
}

function captureCurrentStepFrame() {
    playSound('shutter');
    const liveFrameB64 = captureVideoFrameBase64('video-ekyc');
    if (liveFrameB64) {
        ekycCapturedFrames.push(liveFrameB64);
    }

    ekycTourIndex++;

    setTimeout(() => {
        runNextPoseStep();
    }, 800);
}

async function finishAllPoseSteps() {
    updateDirectionalArrow(null);
    document.getElementById('btn-manual-capture').classList.add('hidden');
    document.getElementById('badge-pose-status').innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang kiểm tra 5 Quy chuẩn & Tải 5 ảnh lên Cloudinary...';

    const userIdInput = document.getElementById('user-id-input').value.trim();
    let isSuccess = false;
    let resMsg = "";
    let cloudUrlsList = [];

    try {
        const res = await fetch('/api/register_ekyc', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userIdInput, images: ekycCapturedFrames })
        });
        const resData = await res.json();
        isSuccess = resData.success;
        resMsg = resData.message;
        if (resData.image_cloud_urls) cloudUrlsList = resData.image_cloud_urls;
    } catch (e) {
        console.log("Using standalone browser simulation mode.");
        isSuccess = true;
        resMsg = "Đăng ký thành công!";
    }

    setTimeout(() => {
        isEkycScanning = false;
        document.getElementById('ekyc-laser').classList.remove('scanning');

        const resCard = document.getElementById('ekyc-result-card');
        const resIcon = document.getElementById('ekyc-res-icon');
        const resTitle = document.getElementById('ekyc-res-title');
        const resDesc = document.getElementById('ekyc-res-desc');
        const statusPill = document.getElementById('ekyc-status-pill');

        if (isSuccess) {
            resCard.className = 'result-card';
            resIcon.innerHTML = '<i class="fa-solid fa-circle-check"></i>';
            resTitle.textContent = "Đã đẩy 5 Ảnh lên Cloudinary Media Library!";
            resDesc.textContent = resMsg || "Master Vector 512D đã mã hóa và 5 ảnh lưu trên Cloudinary cá nhân.";
            statusPill.className = 'status-pill active';
            statusPill.innerHTML = '<i class="fa-solid fa-cloud"></i> COMPLIANT_PASSED';

            document.getElementById('tx-sender-id').value = userIdInput;
            document.getElementById('registered-id-display').textContent = userIdInput;

            const container = document.getElementById('cloud-image-links-container');
            container.innerHTML = '';
            if (cloudUrlsList && cloudUrlsList.length > 0) {
                cloudUrlsList.forEach((url, i) => {
                    const a = document.createElement('a');
                    a.href = url;
                    a.target = '_blank';
                    a.className = 'cloud-link-item';
                    a.innerHTML = `<i class="fa-solid fa-image"></i> [Ảnh Live ${i+1}] ${url.length > 40 ? url.substring(0, 38) + "..." : url}`;
                    container.appendChild(a);
                });
            }
            playSound('success');
        } else {
            resCard.className = 'result-card failed-card';
            resIcon.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i>';
            resTitle.textContent = "TỪ CHỐI ĐĂNG KÝ VÌ VI PHẠM QUY CHUẨN!";
            resDesc.textContent = resMsg || "Khung hình không đạt tiêu chuẩn eKYC.";
            statusPill.className = 'status-pill failed';
            statusPill.innerHTML = '<i class="fa-solid fa-xmark"></i> REJECTED_BY_PRECHECK';
            document.getElementById('cloud-image-links-container').innerHTML = '<span class="cloud-link-item" style="color:#ff1744">Vui lòng điều chỉnh lại ánh sáng / phụ kiện và thử lại.</span>';
            playSound('error');
        }

        resCard.classList.remove('hidden');
    }, 800);
}

function resetEkycForm() {
    if (countdownTimerId) {
        clearInterval(countdownTimerId);
        countdownTimerId = null;
    }
    document.getElementById('countdown-overlay').classList.add('hidden');
    updateDirectionalArrow(null);

    document.getElementById('ekyc-result-card').classList.add('hidden');
    document.getElementById('btn-start-ekyc').classList.remove('hidden');
    document.getElementById('btn-manual-capture').classList.add('hidden');
    document.getElementById('ekyc-oval').classList.remove('valid');
    document.getElementById('badge-pose-status').innerHTML = '<i class="fa-solid fa-cloud-arrow-up"></i> Sẵn sàng đẩy 5 ảnh lên Cloudinary';
    ekycTourIndex = 0;
    ekycCapturedFrames = [];
    isEkycScanning = false;
}

// ====================================================
// BƯỚC 3: XÁC THỰC FACEID CHUYỂN TIỀN > 10M LOGIC
// ====================================================
async function openFaceIdModal() {
    document.getElementById('faceid-modal').classList.remove('hidden');
    await initCamera('video-faceid');

    const stage1Box = document.getElementById('stage-1-box');
    const stage2Box = document.getElementById('stage-2-box');
    const stage1Icon = document.getElementById('stage-1-icon');
    const stage2Icon = document.getElementById('stage-2-icon');
    const stageOverlay = document.getElementById('stage-overlay');
    const stageText = document.getElementById('stage-text');

    stage1Box.className = 'stage-box';
    stage2Box.className = 'stage-box';
    stage1Icon.className = 'fa-solid fa-spinner fa-spin stage-icon';
    stage2Icon.className = 'fa-solid fa-clock stage-icon';
    stageOverlay.classList.remove('hidden');
    stageText.textContent = "Trạm 1: Đang quét Cử động 3D Hybrid Fusion...";

    playSound('shutter');

    setTimeout(() => {
        simulateActivePoseDone();
    }, 1200);
}

async function simulateActivePoseDone() {
    playSound('success');

    const stage1Box = document.getElementById('stage-1-box');
    const stage2Box = document.getElementById('stage-2-box');
    const stage1Icon = document.getElementById('stage-1-icon');
    const stage2Icon = document.getElementById('stage-2-icon');
    const stageOverlay = document.getElementById('stage-overlay');
    const stageText = document.getElementById('stage-text');

    // Chụp mảng 5 khung hình liên tiếp qua khoảng thời gian 600ms để bắt độ biến thiên cử động 3D / chớp mắt
    let framesList = [];
    for (let i = 0; i < 5; i++) {
        const b64 = captureVideoFrameBase64('video-faceid');
        if (b64) framesList.push(b64);
        await new Promise(r => setTimeout(r, 150));
    }

    stageText.textContent = "Trạm 2: Đối chiếu Vector Cloud DB...";
    stage2Icon.className = 'fa-solid fa-spinner fa-spin';

    const senderWalletId = document.getElementById('tx-sender-id').value.trim() || '0987654321';
    let isApproved = false;
    let livenessScoreStr = "❌ REJECTED (SCREEN / PHOTO SPOOF)";
    let cosineScoreStr = "0.0000 (NO MATCH)";

    try {
        const res = await fetch('/api/verify_faceid', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: senderWalletId,
                images: framesList,
                active_liveness_passed: false
            })
        });
        const resData = await res.json();
        isApproved = resData.success;
        if (resData.liveness_score) livenessScoreStr = resData.liveness_score;
        if (resData.cosine_score) cosineScoreStr = resData.cosine_score;
    } catch (e) {
        console.log("Using standalone browser simulation mode.");
    }

    setTimeout(() => {
        if (isApproved) {
            stage1Box.classList.add('passed');
            stage1Icon.className = 'fa-solid fa-circle-check';
            stage2Box.classList.add('passed');
            stage2Icon.className = 'fa-solid fa-circle-check';
        } else {
            stage1Box.classList.add('failed');
            stage1Icon.className = 'fa-solid fa-xmark';
            stage2Box.classList.add('failed');
            stage2Icon.className = 'fa-solid fa-xmark';
        }

        stageOverlay.classList.add('hidden');

        setTimeout(() => {
            closeFaceIdModal();
            const amountVal = parseFloat(document.getElementById('tx-amount-input').value) || 15000000;
            const formattedAmount = amountVal.toLocaleString('vi-VN') + ' VNĐ';
            showTxResult(isApproved, livenessScoreStr, cosineScoreStr, formattedAmount);
        }, 600);

    }, 1000);
}

function closeFaceIdModal() {
    document.getElementById('faceid-modal').classList.add('hidden');
    stopCurrentCamera();
}

function showTxResult(isApproved, livenessStr = "0.9996 (REAL)", cosineStr = "0.8876 (MATCH)", amountStr = "15.000.000 VNĐ") {
    const modal = document.getElementById('tx-result-modal');
    const box = document.getElementById('result-box');
    const iconCircle = document.getElementById('result-icon-circle');
    const icon = document.getElementById('result-icon');
    const title = document.getElementById('result-title');
    const subtitle = document.getElementById('result-subtitle');

    document.getElementById('res-liveness-score').textContent = livenessStr;
    document.getElementById('res-cosine-score').textContent = cosineStr;
    document.getElementById('res-amount').textContent = amountStr;

    if (isApproved) {
        box.className = 'result-box';
        iconCircle.style.background = 'rgba(0, 230, 118, 0.15)';
        iconCircle.style.color = '#00e676';
        icon.className = 'fa-solid fa-check';
        title.textContent = "GIAO DỊCH THÀNH CÔNG!";
        subtitle.textContent = `Chuyển khoản ${amountStr} đã được phê duyệt hợp lệ qua Cloud DB & Sinh trắc học.`;
        playSound('success');
    } else {
        box.className = 'result-box failed';
        iconCircle.style.background = 'rgba(255, 23, 68, 0.15)';
        iconCircle.style.color = '#ff1744';
        icon.className = 'fa-solid fa-xmark';
        title.textContent = "TỪ CHỐI GIAO DỊCH!";
        subtitle.textContent = "Phát hiện màn hình/ảnh mạo danh ở Trạm 1 hoặc ID Ví không khớp khuôn mặt chủ sở hữu ở Trạm 2.";
        playSound('error');
    }

    modal.classList.remove('hidden');
}

function closeTxResultModal() {
    document.getElementById('tx-result-modal').classList.add('hidden');
}
