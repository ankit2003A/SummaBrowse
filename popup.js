document.addEventListener('DOMContentLoaded', () => {
  const videoSourceRadios = document.getElementsByName('videoSource');
  const youtubeInput = document.getElementById('youtubeInput');
  const localInput = document.getElementById('localInput');

  const loadingEl = document.getElementById('loading');
  const errorEl = document.getElementById('error');
  const resultsEl = document.getElementById('results');
  const videoResultsEl = document.getElementById('videoResults');
  const downloadLink = document.getElementById('downloadLink');
  const downloadLink1 = document.getElementById('downloadLink1');

  // Initially hide results and error
  resultsEl.classList.add('hidden');
  videoResultsEl.classList.add('hidden');
  errorEl.classList.add('hidden');
  loadingEl.classList.add('hidden');
  downloadLink.classList.add('hidden');
  downloadLink1.classList.add('hidden');

  videoSourceRadios.forEach(radio => {
    radio.addEventListener('change', () => {
      if (radio.value === 'youtube') {
        youtubeInput.style.display = 'block';
        localInput.style.display = 'none';
      } else {
        youtubeInput.style.display = 'none';
        localInput.style.display = 'block';
      }
    });
  });

  document.getElementById('processFileButton').addEventListener('click', async () => {
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      loadingEl.classList.remove('hidden');
      errorEl.classList.add('hidden');
      resultsEl.classList.add('hidden');
      downloadLink.classList.add('hidden');

      const res = await fetch('http://localhost:5000/process', {
        method: 'POST',
        body: formData
      });

      const data = await res.json();
      loadingEl.classList.add('hidden');

      if (data.error) {
        errorEl.textContent = data.error;
        errorEl.classList.remove('hidden');
      } else {
        document.getElementById('extractedText').textContent = data.extracted_text;
        document.getElementById('summary').textContent = data.summary;
        downloadLink.href = 'http://localhost:5000' + data.download_url;
        downloadLink.classList.remove('hidden');
        resultsEl.classList.remove('hidden');
      }
    } catch (error) {
      loadingEl.classList.add('hidden');
      errorEl.textContent = error.toString();
      errorEl.classList.remove('hidden');
    }
  });

  document.getElementById('processYoutubeButton').addEventListener('click', async () => {
    const url = document.getElementById('youtubeUrl').value;
    if (!url) return;

    try {
      loadingEl.classList.remove('hidden');
      errorEl.classList.add('hidden');
      videoResultsEl.classList.add('hidden');
      downloadLink1.classList.add('hidden');

      const res = await fetch('http://localhost:5000/process_video', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_source: url })
      });

      const data = await res.json();
      loadingEl.classList.add('hidden');

      if (data.error) {
        errorEl.textContent = data.error;
        errorEl.classList.remove('hidden');
      } else {
        document.getElementById('videoSummary').textContent = data.summary;
        downloadLink1.href = 'http://localhost:5000' + data.download_url;
        downloadLink1.classList.remove('hidden');
        videoResultsEl.classList.remove('hidden');
      }
    } catch (error) {
      loadingEl.classList.add('hidden');
      errorEl.textContent = error.toString();
      errorEl.classList.remove('hidden');
    }
  });

  document.getElementById('processLocalButton').addEventListener('click', async () => {
    const file = document.getElementById('localVideoFile').files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('video_file', file);

    try {
      loadingEl.classList.remove('hidden');
      errorEl.classList.add('hidden');
      videoResultsEl.classList.add('hidden');
      downloadLink1.classList.add('hidden');

      const res = await fetch('http://localhost:5000/process_video', {
        method: 'POST',
        body: formData
      });

      const data = await res.json();
      loadingEl.classList.add('hidden');

      if (data.error) {
        errorEl.textContent = data.error;
        errorEl.classList.remove('hidden');
      } else {
        document.getElementById('videoSummary').textContent = data.summary;
        downloadLink1.href = 'http://localhost:5000' + data.download_url;
        downloadLink1.classList.remove('hidden');
        videoResultsEl.classList.remove('hidden');
      }
    } catch (error) {
      loadingEl.classList.add('hidden');
      errorEl.textContent = error.toString();
      errorEl.classList.remove('hidden');
    }
  });
});
