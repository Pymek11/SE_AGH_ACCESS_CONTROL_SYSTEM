'use client';
import { Scanner, useDevices } from "@yudiel/react-qr-scanner";
import React from "react";



export default function CameraPage() {
  const handleScan = (detected: any) => {
    if (!detected) return;
    // `@yudiel/react-qr-scanner` provides an array of detected barcodes.
    let text: string | null = null;
    if (Array.isArray(detected) && detected.length > 0) {
      const first = detected[0];
      text = first?.rawValue ?? first?.data ?? first?.value ?? (typeof first === 'string' ? first : null);
    } else if (typeof detected === 'string') {
      text = detected;
    }

    if (text) {
      console.log("Scanned QR Code:", text);
      // You can add further processing of the scanned result here
    }
  };

  const devices = useDevices();
  const [selectedDeviceId, setSelectedDeviceId] = React.useState<string | null>(null);

  const handleError = (error: unknown) => {
    console.error("QR Scanner Error:", error);
  };

  const [status, setStatus] = React.useState<string | null>(null);
  const previewRef = React.useRef<HTMLVideoElement | null>(null);
  const streamRef = React.useRef<MediaStream | null>(null);

  const openPreview = async () => {
    setStatus(null);
    try {
      const constraints: MediaStreamConstraints = selectedDeviceId
        ? { video: { deviceId: { exact: selectedDeviceId } } }
        : { video: { facingMode: 'environment' } };
      setStatus('Requesting camera...');
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;
      if (previewRef.current) {
        previewRef.current.srcObject = stream;
        await previewRef.current.play().catch(() => {});
      }
      setStatus('Preview started');
    } catch (e: any) {
      console.error('getUserMedia error', e);
      setStatus(`Error: ${e?.name || e?.message || String(e)}`);
    }
  };

  const stopPreview = () => {
    try {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(t => t.stop());
        streamRef.current = null;
      }
      if (previewRef.current) previewRef.current.srcObject = null;
      setStatus('Preview stopped');
    } catch (e) {
      console.error(e);
    }
  };

 return (
    <div>
      <select value={selectedDeviceId ?? ''} onChange={(e) => setSelectedDeviceId(e.target.value)}>
        <option value="">Select a camera</option>
        {devices.map((device, i) => (
          <option key={device.deviceId || i} value={device.deviceId}>
            {device.label || `Camera ${i + 1}`}
          </option>
        ))}
      </select>

      <Scanner
        onScan={handleScan}
        onError={handleError}
        constraints={selectedDeviceId ? { deviceId: { exact: selectedDeviceId } } : { facingMode: 'environment' }}
      />
    </div>
  );
}