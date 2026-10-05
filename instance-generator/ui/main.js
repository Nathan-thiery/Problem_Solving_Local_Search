const { app, BrowserWindow, dialog } = require('electron');
const { execFile, spawn } = require('child_process');

const appUrl = process.env.INSTANCE_GENERATOR_URL;
const image = process.env.INSTANCE_GENERATOR_IMAGE || 'louisesanchez/instance-generator:1.0.0';
const containerName = 'instance-generator-desktop';
const port = 8080;
let dockerProcess;

// Correctif pour Arch Linux / Wayland / Vulkan
app.disableHardwareAcceleration();
app.commandLine.appendSwitch('ozone-platform-hint', 'auto');

function runDocker() {
  return new Promise((resolve, reject) => {
    execFile('docker', ['rm', '-f', containerName], () => {
      dockerProcess = spawn('docker', [
        'run', '-d', '--rm', '-p', `${port}:80`, '--name', containerName, image,
      ], { windowsHide: true });

      let errorOutput = '';
      dockerProcess.stderr.on('data', (data) => {
        errorOutput += data.toString();
      });
      dockerProcess.on('error', reject);
      dockerProcess.on('close', (code) => {
        if (code === 0) {
          resolve();
        } else {
          reject(new Error(errorOutput || `docker run a échoué (${code})`));
        }
      });
    });
  });
}

async function waitForApi() {
  const healthUrl = `http://localhost:${port}/api/health`;
  for (let attempt = 0; attempt < 60; attempt += 1) {
    try {
      const response = await fetch(healthUrl);
      if (response.ok) {
        return healthUrl.replace('/api/health', '');
      }
    } catch {
      // Docker Desktop may need a few seconds to start the container.
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error('Le conteneur Docker ne répond pas après 30 secondes.');
}

function createWindow(url) {
  const win = new BrowserWindow({
    width: 900,
    height: 700,
    autoHideMenuBar: true,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  win.loadURL(url);
}

app.whenReady().then(async () => {
  try {
    const url = appUrl || (await runDocker(), await waitForApi());
    createWindow(url);
  } catch (error) {
    await dialog.showMessageBox({
      type: 'error',
      title: 'Instance Generator',
      message: 'Impossible de démarrer Docker.',
      detail: error.message,
    });
    app.quit();
  }
});

app.on('window-all-closed', () => {
  app.quit();
});

app.on('before-quit', () => {
  execFile('docker', ['rm', '-f', containerName]);
});
