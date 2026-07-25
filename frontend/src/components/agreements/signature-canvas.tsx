"use client";

import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import SignaturePad from "signature_pad";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface SignatureCanvasHandle {
  /** null when the pad is empty — the caller decides how to surface that. */
  toDataURL: () => string | null;
  clear: () => void;
}

interface SignatureCanvasProps {
  className?: string;
  onChange?: () => void;
}

/** Thin wrapper around signature_pad for drawn-signature capture (master
 * prompt Section 6). The canvas is resized for the device pixel ratio on
 * mount so strokes stay crisp on high-DPI screens, and re-cleared on window
 * resize since signature_pad doesn't preserve strokes across a canvas
 * dimension change. */
export const SignatureCanvas = forwardRef<SignatureCanvasHandle, SignatureCanvasProps>(
  function SignatureCanvas({ className, onChange }, ref) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const padRef = useRef<SignaturePad | null>(null);
    const onChangeRef = useRef(onChange);
    onChangeRef.current = onChange;

    useEffect(() => {
      const canvas = canvasRef.current;
      if (!canvas) return;

      const pad = new SignaturePad(canvas, { backgroundColor: "rgb(255, 255, 255)" });
      padRef.current = pad;
      pad.addEventListener("endStroke", () => onChangeRef.current?.());

      const resize = () => {
        const ratio = Math.max(window.devicePixelRatio || 1, 1);
        canvas.width = canvas.offsetWidth * ratio;
        canvas.height = canvas.offsetHeight * ratio;
        canvas.getContext("2d")?.scale(ratio, ratio);
        pad.clear();
      };
      resize();
      window.addEventListener("resize", resize);

      return () => {
        window.removeEventListener("resize", resize);
        pad.off();
        padRef.current = null;
      };
    }, []);

    useImperativeHandle(ref, () => ({
      toDataURL: () => {
        const pad = padRef.current;
        if (!pad || pad.isEmpty()) return null;
        return pad.toDataURL("image/png");
      },
      clear: () => {
        padRef.current?.clear();
        onChange?.();
      },
    }));

    return (
      <div className={cn("flex flex-col gap-2", className)}>
        <canvas
          ref={canvasRef}
          className="border-border bg-background h-40 w-full touch-none rounded-md border"
          aria-label="Draw your signature"
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="self-start"
          onClick={() => {
            padRef.current?.clear();
            onChange?.();
          }}
        >
          Clear
        </Button>
      </div>
    );
  },
);
