"use client";

import { useState, FormEvent, ChangeEvent, useEffect, useRef } from "react";
import { validatePassword, checkAuthRedirect, PasswordValidationResponse } from "../../services/api.service";
import TreeGraph from "./invite/[code]/TreeGraph";

type PageState = "password" | "loading" | "success";

export default function Home() {
  const [password, setPassword] = useState("");
  const [displayValue, setDisplayValue] = useState("");
  const [isValidating, setIsValidating] = useState(false);
  const [countdown, setCountdown] = useState<number | null>(null);
  const [validationState, setValidationState] = useState<"error" | "success" | null>(null);
  const [showCursor, setShowCursor] = useState(true);
  const [shouldResetOnNextInput, setShouldResetOnNextInput] = useState(false);
  const [pageState, setPageState] = useState<PageState>("loading");
  const [authData, setAuthData] = useState<PasswordValidationResponse | null>(null);
  const [copied, setCopied] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const errorTimerRef = useRef<NodeJS.Timeout | null>(null);
  const textContainerRef = useRef<HTMLDivElement>(null);

  // Check for existing authentication on mount
  useEffect(() => {
    const checkExistingAuth = async () => {
      const { data } = await checkAuthRedirect();
      if (data?.valid && data.redirect_url && data.token) {
        // User is already authenticated - show success screen with their data
        setAuthData({
          password: data.password || "",
          redirect_url: data.redirect_url,
          token: data.token,
          trees: data.trees || [],
        });
        setPageState("success");
      } else {
        setPageState("password");
      }
    };

    checkExistingAuth();
  }, []);

  // Blinking cursor effect
  useEffect(() => {
    const interval = setInterval(() => {
      setShowCursor((prev) => !prev);
    }, 530);

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
    if (countdown === null && !isValidating && pageState === "password") {
      inputRef.current?.focus();
    }
  }, [countdown, isValidating, pageState]);

  // Auto-scroll to show the end of the password
  useEffect(() => {
    if (textContainerRef.current) {
      textContainerRef.current.scrollLeft = textContainerRef.current.scrollWidth;
    }
  }, [displayValue]);

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const newDisplayValue = e.target.value;
    const oldLength = displayValue.length;
    const newLength = newDisplayValue.length;

    if (shouldResetOnNextInput) {
      setShouldResetOnNextInput(false);
      
      if (newLength < oldLength) {
        setPassword("");
        setDisplayValue("");
      } else {
        const newChar = newDisplayValue.slice(-1);
        setPassword(newChar);
        setDisplayValue("*".repeat(newChar.length));
      }
    } else {
      let newPassword = password;
      
      if (newLength > oldLength) {
        const addedChars = newDisplayValue.slice(oldLength);
        newPassword = password + addedChars;
      } else if (newLength < oldLength) {
        newPassword = password.slice(0, newLength);
      }
      
      setPassword(newPassword);
      setDisplayValue("*".repeat(newLength));
    }

    setValidationState(null);

    if (errorTimerRef.current) {
      clearTimeout(errorTimerRef.current);
      errorTimerRef.current = null;
    }
  };

  const handleBlur = () => {
    requestAnimationFrame(() => {
      if (pageState === "password") {
        inputRef.current?.focus();
      }
    });
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (!password || isValidating) return;

    setIsValidating(true);

    if (errorTimerRef.current) {
      clearTimeout(errorTimerRef.current);
      errorTimerRef.current = null;
    }

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
      const { data, error } = await validatePassword(password);

      if (!error && data && data.redirect_url) {
        // Success - show success screen instead of redirecting
        clearInterval(countdownInterval);
        setCountdown(null);
        setValidationState("success");
        setAuthData(data);
        setPageState("success");
        return;
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

        setShouldResetOnNextInput(true);
        setValidationState("error");

        errorTimerRef.current = setTimeout(() => {
          setValidationState(null);
          errorTimerRef.current = null;
        }, 2000);
      }
    } catch {
      const waitForCountdown = new Promise<void>((resolve) => {
        const checkInterval = setInterval(() => {
          if (countdownComplete) {
            clearInterval(checkInterval);
            resolve();
          }
        }, 100);
      });

      await waitForCountdown;

      setShouldResetOnNextInput(true);
      setValidationState("error");

      errorTimerRef.current = setTimeout(() => {
        setValidationState(null);
        errorTimerRef.current = null;
      }, 2000);
    } finally {
      clearInterval(countdownInterval);
      setCountdown(null);
      setIsValidating(false);
      requestAnimationFrame(() => {
        inputRef.current?.focus();
      });
    }
  };

  const copyPassword = async () => {
    if (authData?.password) {
      await navigator.clipboard.writeText(authData.password);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const continueToSite = () => {
    if (authData?.redirect_url) {
      const redirectUrl = new URL(authData.redirect_url);
      if (authData.token) {
        redirectUrl.hash = `token=${authData.token}`;
      }
      window.location.href = redirectUrl.toString();
    }
  };

  const enterAnotherPassword = () => {
    setPageState("password");
    setAuthData(null);
    setPassword("");
    setDisplayValue("");
    setValidationState(null);
    // Focus the input after state update
    setTimeout(() => {
      inputRef.current?.focus();
    }, 0);
  };

  // Loading State
  if (pageState === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background font-mono">
        <div className="w-6 h-6 border-2 border-foreground/30 border-t-foreground rounded-full animate-spin" />
      </div>
    );
  }

  // Success State
  if (pageState === "success" && authData) {
    return (
      <div className="min-h-screen bg-background font-mono flex items-center justify-center p-6">
        <div className="w-full max-w-3xl flex flex-col lg:flex-row gap-12 lg:gap-16 items-center lg:items-start">
          
          {/* Left - Password & Instructions */}
          <div className="flex-1 w-full max-w-md space-y-8">
            {/* Password - only show if we have it */}
            {authData.password && (
              <div className="space-y-3">
                <p className="text-foreground/50 text-sm uppercase tracking-wider">Your password</p>
                <div 
                  onClick={copyPassword}
                  className="border border-foreground/20 hover:border-foreground/40 p-4 cursor-pointer transition-colors group flex items-center justify-between"
                >
                  <code className="text-xl sm:text-2xl text-foreground tracking-wide select-all">
                    {authData.password}
                  </code>
                  <div className="text-foreground/30 group-hover:text-foreground/60 transition-colors ml-4 flex-shrink-0">
                    {copied ? (
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    ) : (
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Instructions */}
            <div className="space-y-4 text-foreground/60 text-sm leading-relaxed">
              {authData.password ? (
                <>
                  <p>
                    <span className="text-foreground">Welcome to the trust.</span>{" "}
                    Please help maintain site security by following the guidelines below.
                  </p>
                  <p>
                    <span className="text-foreground">Don&apos;t forget your password.</span>{" "}
                    You may need it to access the site again.
                  </p>
                  <p>
                    <span className="text-foreground">Once redirected, don&apos;t share the URL.</span>{" "}
                    Invite others by generating invite codes with the share button on the site, or sharing this password.
                    <br /><br />
                    The website may randomly rotate IPs to remain concealed, so any bookmarks or shared links should always use cascadingtrust.net.
                  </p>
                </>
              ) : (
                <p>
                  <span className="text-foreground">You&apos;re already authenticated.</span>{" "}
                  Continue to the site or enter a different password to access another site.
                </p>
              )}
            </div>

            {/* Actions */}
            <div className="space-y-3">
              <button
                onClick={continueToSite}
                className="w-full border border-foreground/20 hover:border-foreground hover:bg-foreground hover:text-background py-3 text-foreground transition-all text-sm uppercase tracking-wider"
              >
                Continue →
              </button>
              
              <button
                onClick={enterAnotherPassword}
                className="w-full text-foreground/50 hover:text-foreground py-2 text-sm transition-colors underline underline-offset-4"
              >
                Enter another password
              </button>
            </div>
          </div>

          {/* Right - Graph */}
          <div className="flex-shrink-0">
            {authData.trees && authData.trees.length > 0 && (
              <TreeGraph trees={authData.trees} />
            )}
          </div>
        </div>
      </div>
    );
  }

  // Password Entry State
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="w-full max-w-md px-4">
        <form onSubmit={handleSubmit} className="relative">
          {/* Countdown display */}
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
