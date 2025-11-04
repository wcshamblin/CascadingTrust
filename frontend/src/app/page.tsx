"use client";

import { useState, FormEvent, ChangeEvent, useEffect, useRef } from "react";
import { validatePassword } from "../../services/api.service";

export default function Home() {
  const [password, setPassword] = useState("");
  const [displayValue, setDisplayValue] = useState("");
  const [isValidating, setIsValidating] = useState(false);
  const [countdown, setCountdown] = useState<number | null>(null);
  const [validationState, setValidationState] = useState<"error" | "success" | null>(null);
  const [showCursor, setShowCursor] = useState(true);
  const [shouldResetOnNextInput, setShouldResetOnNextInput] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const errorTimerRef = useRef<NodeJS.Timeout | null>(null);
  const textContainerRef = useRef<HTMLDivElement>(null);

  // Blinking cursor effect
  useEffect(() => {
    const interval = setInterval(() => {
      setShowCursor((prev) => !prev);
    }, 530); // Blink every 530ms

    return () => clearInterval(interval);
  }, []);

  // Cleanup error timer on unmount
  useEffect(() => {
    return () => {
      if (errorTimerRef.current) {
        clearTimeout(errorTimerRef.current);
      }
    };
  }, []);

  // Refocus input when countdown ends
  useEffect(() => {
    if (countdown === null && !isValidating) {
      inputRef.current?.focus();
    }
  }, [countdown, isValidating]);

  // Auto-scroll to show the end of the password (most recent characters)
  useEffect(() => {
    if (textContainerRef.current) {
      textContainerRef.current.scrollLeft = textContainerRef.current.scrollWidth;
    }
  }, [displayValue]);

  // Real API call to backend validation endpoint using the service layer
  const validatePasswordAPI = async (pwd: string): Promise<{ isValid: boolean; redirectUrl?: string; token?: string }> => {
    const { data, error } = await validatePassword(pwd);
    
    if (error) {
      console.error("Password validation error:", error.message);
      return { isValid: false };
    }
    
    if (data) {
      return { 
        isValid: true, 
        redirectUrl: data.redirect_url,
        token: data.token  // Include JWT token for cross-domain redirect
      };
    }
    
    return { isValid: false };
  };

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const newDisplayValue = e.target.value;
    const oldLength = displayValue.length;
    const newLength = newDisplayValue.length;

    // If we should reset on next input
    if (shouldResetOnNextInput) {
      setShouldResetOnNextInput(false);
      
      // If backspace was pressed (length decreased), clear everything
      if (newLength < oldLength) {
        setPassword("");
        setDisplayValue("");
      } else {
        // Get the newly typed character (should be the last char in the input)
        const newChar = newDisplayValue.slice(-1);
        setPassword(newChar);
        setDisplayValue("*".repeat(newChar.length));
      }
    } else {
      // Calculate the actual password based on the change
      let newPassword = password;
      
      if (newLength > oldLength) {
        // Characters were added - extract the newly typed characters
        const addedChars = newDisplayValue.slice(oldLength);
        newPassword = password + addedChars;
      } else if (newLength < oldLength) {
        // Characters were removed (backspace/delete)
        newPassword = password.slice(0, newLength);
      }
      
      setPassword(newPassword);
      setDisplayValue("*".repeat(newLength));
    }

    setValidationState(null);

    // Clear any existing error timer
    if (errorTimerRef.current) {
      clearTimeout(errorTimerRef.current);
      errorTimerRef.current = null;
    }
  };

  const handleBlur = () => {
    // Immediately refocus the input if it loses focus
    requestAnimationFrame(() => {
      inputRef.current?.focus();
    });
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (!password || isValidating) return;

    setIsValidating(true);

    // Clear any existing error timer
    if (errorTimerRef.current) {
      clearTimeout(errorTimerRef.current);
      errorTimerRef.current = null;
    }

    // Start countdown (2 seconds)
    setCountdown(2);
    let countdownComplete = false;
    const countdownInterval = setInterval(() => {
      setCountdown((prev) => {
        if (prev === null || prev <= 1) {
          clearInterval(countdownInterval);
          countdownComplete = true;
          return null;
        }
        return prev - 1;
      });
    }, 1000);

    try {
      // Make API call
      const result = await validatePasswordAPI(password);

      if (result.isValid && result.redirectUrl) {
        // Success - redirect immediately
        clearInterval(countdownInterval);
        setCountdown(null);
        setValidationState("success");
        console.log("Password valid - redirecting to:", result.redirectUrl);
        
        // Redirect with JWT token in URL fragment for cross-domain access
        // The destination site can read it via window.location.hash
        const redirectUrl = new URL(result.redirectUrl);
        if (result.token) {
          redirectUrl.hash = `token=${result.token}`;
        }
        
        window.location.href = redirectUrl.toString();
        return; // Exit early, no need to continue
      } else {
        // Error - wait for countdown to complete before showing error
        const waitForCountdown = new Promise<void>((resolve) => {
          const checkInterval = setInterval(() => {
            if (countdownComplete) {
              clearInterval(checkInterval);
              resolve();
            }
          }, 100);
        });

        await waitForCountdown;

        // Mark to reset on next input instead of clearing immediately
        setShouldResetOnNextInput(true);
        setValidationState("error");

        // Clear error state after 2 seconds
        errorTimerRef.current = setTimeout(() => {
          setValidationState(null);
          errorTimerRef.current = null;
        }, 2000);
      }
    } catch (error) {
      // Wait for countdown to complete before showing error
      const waitForCountdown = new Promise<void>((resolve) => {
        const checkInterval = setInterval(() => {
          if (countdownComplete) {
            clearInterval(checkInterval);
            resolve();
          }
        }, 100);
      });

      await waitForCountdown;

      // Mark to reset on next input instead of clearing immediately
      setShouldResetOnNextInput(true);
      setValidationState("error");

      // Clear error state after 2 seconds
      errorTimerRef.current = setTimeout(() => {
        setValidationState(null);
        errorTimerRef.current = null;
      }, 2000);
    } finally {
      clearInterval(countdownInterval);
      setCountdown(null);
      setIsValidating(false);
      // Immediately refocus the input field
      requestAnimationFrame(() => {
        inputRef.current?.focus();
      });
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="w-full max-w-md px-4">
        <form onSubmit={handleSubmit} className="relative">
          {/* Countdown display - positioned absolutely above the input */}
          {countdown !== null && (
            <div className="absolute left-1/2 -translate-x-1/2 -top-20 flex items-center justify-center">
              <span className="text-4xl font-bold text-foreground/50">
                {countdown}
              </span>
            </div>
          )}
          
          <div className="relative">
            <input
              ref={inputRef}
              type="text"
              value={displayValue}
              onChange={handleChange}
              onBlur={handleBlur}
              disabled={countdown !== null}
              className={`password-input w-full px-6 py-4 text-3xl bg-transparent border-[3px] text-center text-foreground focus:outline-none transition-colors overflow-hidden ${
                validationState === "error"
                  ? "border-red-500 focus:border-red-500"
                  : validationState === "success"
                  ? "border-green-500 focus:border-green-500"
                  : countdown !== null || isValidating
                  ? "border-gray-400 focus:border-gray-400"
                  : "border-white focus:border-white"
              } ${countdown !== null ? "opacity-50 cursor-not-allowed" : ""}`}
              autoFocus
              autoComplete="off"
              style={{ textOverflow: 'clip' }}
            />
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none overflow-hidden px-6">
              <div ref={textContainerRef} className="relative inline-flex items-center justify-end text-3xl max-w-full overflow-x-auto scrollbar-hide">
                <span className="text-foreground font-mono whitespace-nowrap">
                  {displayValue}
                </span>
                <span
                  className={`inline-block w-[0.51em] h-[1.02em] ml-[1px] transition-opacity flex-shrink-0 ${
                    countdown === null && showCursor ? "bg-foreground opacity-100" : "opacity-0"
                  }`}
                />
              </div>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
