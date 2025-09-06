const ytUrl = document.getElementById('url-input');
const searchBtn = document.getElementById('search-btn');                 
const videoDropdown = document.getElementById('video-dropdown-content');
const audioDropdown = document.getElementById('audio-dropdown-content');
const videoTitle = document.getElementById('video-title');

// ---------- Fetch formats ----------
searchBtn.onclick = async () => {
    let url = ytUrl.value.trim();
    if (!url) { alert("Link jaruri hai."); return; }

    let res = await fetch('http://127.0.0.1:5000/formats', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
    });

    let data = await res.json();
    if (data.error) { alert(data.error); return; }

    videoTitle.innerText = data.title;

    // Video formats
    videoDropdown.innerHTML = "";
    data.formats.filter(f => f.height).forEach(f => {
        let txt = `${f.height}p ${f.note || ""} (${f.ext})`;
        let a = document.createElement('a');
        a.href = "#";
        a.innerText = txt;
        a.onclick = () => downloadFile(url, f.id);
        videoDropdown.appendChild(a);
    });

    // Audio formats
    audioDropdown.innerHTML = "";
    data.formats.filter(f => f.abr).forEach(f => {
        let txt = `${f.abr} kbps (${f.ext})`;
        let a = document.createElement('a');
        a.href = "#";
        a.innerText = txt;
        a.onclick = () => downloadFile(url, f.id);
        audioDropdown.appendChild(a);
    });
};



// ---------- Toggle dropdowns ----------
document.getElementById('video-dropbtn').onclick = function() {
    videoDropdown.style.display = videoDropdown.style.display === 'block' ? 'none' : 'block';
};
document.getElementById('audio-dropbtn').onclick = function() {
    audioDropdown.style.display = audioDropdown.style.display === 'block' ? 'none' : 'block';
};

// ---------- Download ----------
async function downloadFile(url, formatId) {
    let res = await fetch('http://127.0.0.1:5000/download', {
        method: 'POST',
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url, format_id: formatId })
    });

    if (!res.ok) {
        alert("Download failed");
        return;
    }

    let blob = await res.blob();
    let link = document.createElement("a");
    link.href = window.URL.createObjectURL(blob);
    link.download = "video";
    link.click();

    setTimeout(() => {
    window.location.reload();
   }, 2000);
}








/*const ytUrl = document.getElementById('url-input');
const searchBtn = document.getElementById('search-btn');
const videoDropdown = document.getElementById('video-dropdown-content');
const audioDropdown = document.getElementById('audio-dropdown-content');

searchBtn.onclick = async () => {
    let url = ytUrl.value.trim();
    if (!url) { 
        alert("Link jaruri hai."); 
        return; 
    }

    let res = await fetch('/formats', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
    });

    let data = await res.json();
    if (data.error) { 
        alert(data.error); 
        return; 
    }

    // 🎥 Video formats (video only)
    videoDropdown.innerHTML = "";
    data.formats
        .filter(f => f.vcodec !== "none" && f.acodec === "none")
        .forEach(f => {
            let txt = (f.height ? `${f.height}p` : "") + 
                      (f.ext ? ` ${f.ext}` : "") + 
                      ` (${f.id})`;
            let a = document.createElement('a');
            a.href = "#";
            a.dataset.type = "quality";
            a.dataset.value = f.id;
            a.innerHTML = `<i class="fas fa-video"></i> ${txt}`;
            videoDropdown.appendChild(a);
        });

    // 🎵 Audio formats (audio only)
    audioDropdown.innerHTML = "";
    data.formats
        .filter(f => f.acodec !== "none" && f.vcodec === "none")
        .forEach(f => {
            let txt = (f.abr ? `${f.abr}kbps ` : "") + 
                      (f.ext || "") + 
                      ` (${f.id})`;
            let a = document.createElement('a');
            a.href = "#";
            a.dataset.type = "format";
            a.dataset.value = f.id;
            a.innerHTML = `<i class="fas fa-music"></i> ${txt}`;
            audioDropdown.appendChild(a);
        });
};

// ✅ Toggle buttons (sirf button pe click par)
document.getElementById('video-dropbtn').onclick = function() {
    const menu = document.getElementById('video-dropdown-content');
    menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
};

document.getElementById('audio-dropbtn').onclick = function() {
    const menu = document.getElementById('audio-dropdown-content');
    menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
};

// ✅ Bahar click karte hi close
window.onclick = function(event) {
    if (!event.target.matches('.dropbtn')) {
        document.getElementById('video-dropdown-content').style.display = 'none';
        document.getElementById('audio-dropdown-content').style.display = 'none';
    }
};













/*const ytUrl = document.getElementById('url-input');
const searchBtn = document.getElementById('search-btn');
const videoDropdown = document.getElementById('video-dropdown-content');
const audioDropdown = document.getElementById('audio-dropdown-content');

searchBtn.onclick = async () => {
    let url = ytUrl.value.trim();
    if (!url) { alert("Link jaruri hai."); return; }

    let res = await fetch('/formats', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
    });

    let data = await res.json();
    if (data.error) { alert(data.error); return; }

    // Video formats
    videoDropdown.innerHTML = "";
    data.formats.filter(f => f.video_only).forEach(f => {
        let txt = (f.height ? `${f.height}p` : "") + ' ' + (f.note||"") + ` (${f.id})`;
        let a = document.createElement('a');
        a.href = "#";
        a.dataset.type = "quality";
        a.dataset.value = f.id;
        a.innerHTML = `<i class="fas fa-video"></i> ${txt}`;
        videoDropdown.appendChild(a);
    });

    // Audio formats
    audioDropdown.innerHTML = "";
    data.formats.filter(f => f.audio_only).forEach(f => {
        let txt = (f.abr ? `${f.abr}kbps ` : "") + (f.ext||"") + ` (${f.id})`;
        let a = document.createElement('a');
        a.href = "#";
        a.dataset.type = "format";
        a.dataset.value = f.id;
        a.innerHTML = `<i class="fas fa-music"></i> ${txt}`;
        audioDropdown.appendChild(a);
    });
};

// ✅ Toggle buttons (sirf button pe click par)
document.getElementById('video-dropbtn').onclick = function() {
    const menu = document.getElementById('video-dropdown-content');
    menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
};

document.getElementById('audio-dropbtn').onclick = function() {
    const menu = document.getElementById('audio-dropdown-content');
    menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
};

// ✅ Bahar click karte hi close
window.onclick = function(event) {
    if (!event.target.matches('.dropbtn')) {
        document.getElementById('video-dropdown-content').style.display = 'none';
        document.getElementById('audio-dropdown-content').style.display = 'none';
    }
};
/*const ytUrl = document.getElementById('url-input');
const searchBtn = document.getElementById('search-btn');
const videoDropdown = document.getElementById('video-dropdown-content');
const audioDropdown = document.getElementById('audio-dropdown-content');


searchBtn.onclick = async () => {
    let url = ytUrl.value.trim();
    if (!url) { alert("Link jaruri hai."); return; }
    let res = await fetch('/formats', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url })
    });
    let data = await res.json();
    if (data.error) { alert(data.error); return; }

    // Video formats
    videoDropdown.innerHTML = "";
    data.formats.filter(f => f.video_only).forEach(f => {
        let txt = (f.height ? `${f.height}p` : "") + ' ' + (f.note||"") + ` (${f.id})`;
        let a = document.createElement('a');
        a.href = "#";
        a.dataset.type = "quality";
        a.dataset.value = f.id;
        a.innerHTML = `<i class="fas fa-video"></i> ${txt}`;
        videoDropdown.appendChild(a);
    });

    // Audio formats
    audioDropdown.innerHTML = "";
    data.formats.filter(f => f.audio_only).forEach(f => {
        let txt = (f.abr ? `${f.abr}kbps ` : "") + (f.ext||"") + ' (' + f.id + ')';
        let a = document.createElement('a');
        a.href = "#";
        a.dataset.type = "format";
        a.dataset.value = f.id;
        a.innerHTML = `<i class="fas fa-music"></i> ${txt}`;
        audioDropdown.appendChild(a);

    });
    document.getElementById('video-dropdown-content').onclick = function() {
    const menu = document.getElementById('video-dropdown-content');
    menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
};

document.getElementById('audio-dropbtn').onclick = function() {
    const menu = document.getElementById('audio-dropdown-content');
    menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
};

// Optional: Jab user kahin aur click kare to menu band ho jaye
window.onclick = function(event) {
    if (!event.target.matches('.dropbtn')) {
        document.getElementById('video-dropdown-content').style.display = 'none';
        document.getElementById('audio-dropdown-content').style.display = 'none';
    }
};

};
































/*
// Jab user YouTube link dale ya "Search" button dabaye:
const url = document.getElementById('url-input').value.trim();

fetch('/formats', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url })
})
.then(res => res.json())
.then(data => {
    // data.formats == Array of formats (with id, ext, resolution etc.)
    // Example: [{id:"313",ext:"webm",resolution:2160,...}, ...]
    // Fill video dropdown:
    const vq = document.getElementById("videoQualityDropdown");
    vq.innerHTML = '';
    data.formats.filter(f => f.video_only).forEach(f => {
        vq.innerHTML += `<option value="${f.id}">${f.resolution || ''}p ${f.ext} (${f.id})</option>`;
    });
    // Fill audio dropdown:
    const aq = document.getElementById("audioFormatDropdown");
    aq.innerHTML = '';
    data.formats.filter(f => f.audio_only).forEach(f => {
        aq.innerHTML += `<option value="${f.id}">${f.ext} (${f.id})</option>`;
    });
//}); */
