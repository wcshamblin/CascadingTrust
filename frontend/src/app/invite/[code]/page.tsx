"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { validateInvite, InviteValidationResponse } from "../../../../services/api.service";
import TreeGraph from "./TreeGraph";

type InviteState = "loading" | "accepted" | "error";

export default function InvitePage() {
  const params = useParams();
  const code = params.code as string;
  const [state, setState] = useState<InviteState>("loading");
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [inviteData, setInviteData] = useState<InviteValidationResponse | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!code) return;

    const processInvite = async () => {
      // Validate the invite code - each invite is specific to a site,
      // so we always process the invite to get the correct site's credentials
      setState("loading");
      
      const { data, error } = await validateInvite(code);

      if (error) {
        setState("error");
        setErrorMessage(error.message || "Invalid or expired invite code");
        return;
      }

      if (data && data.password) {
        setInviteData(data);
        setState("accepted");
      } else {
        setState("error");
        setErrorMessage("Invalid invite response");
      }
    };

    processInvite();
  }, [code]);

  const copyPassword = async () => {
    if (inviteData?.password) {
      await navigator.clipboard.writeText(inviteData.password);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const continueToSite = () => {
    if (inviteData?.redirect_url) {
      const redirectUrl = new URL(inviteData.redirect_url);
      if (inviteData.token) {
        redirectUrl.hash = `token=${inviteData.token}`;
      }
      window.location.href = redirectUrl.toString();
    }
  };

  // Loading State
  if (state === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background font-mono">
        <div className="w-6 h-6 border-2 border-foreground/30 border-t-foreground rounded-full animate-spin" />
      </div>
    );
  }

  // Error State
  if (state === "error") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background font-mono p-6">
        <div className="text-center max-w-sm space-y-6">
          <div>
            <p className="text-red-500 mb-2">{errorMessage}</p>
            <p className="text-foreground/40 text-sm">
              This invite may be expired or already used.
            </p>
          </div>

          <Link
            href="/"
            className="text-foreground/50 hover:text-foreground text-sm underline underline-offset-4 transition-colors"
          >
            Already have a password?
          </Link>
        </div>
      </div>
    );
  }

  // Accepted State
  return (
    <div className="min-h-screen bg-background font-mono flex items-center justify-center p-6">
      <div className="w-full max-w-3xl flex flex-col lg:flex-row gap-12 lg:gap-16 items-center lg:items-start">
        
        {/* Left - Password & Instructions */}
        <div className="flex-1 w-full max-w-md space-y-8">
          {/* Password */}
          <div className="space-y-3">
            <p className="text-foreground/50 text-sm uppercase tracking-wider">Your password</p>
            <div 
              onClick={copyPassword}
              className="border border-foreground/20 hover:border-foreground/40 p-4 cursor-pointer transition-colors group flex items-center justify-between"
            >
              <code className="text-xl sm:text-2xl text-foreground tracking-wide select-all">
                {inviteData?.password}
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

          {/* Instructions */}
          <div className="space-y-4 text-foreground/60 text-sm leading-relaxed">
            <p>
              <span className="text-foreground">Welcome to the trust.</span>{" "}
              Please help maintain site security by following the guidelines below.
            </p>
            <p>
              <span className="text-foreground">Write your password down.</span>{" "}
              You may need it to access the site again.
            </p>
            <p>
              <span className="text-foreground">Once redirected, don&apos;t share the URL.</span>{" "}
              Invite others by generating invite codes with the share button on the site, or sharing this invite link.
              <br /><br />
              The website may randomly rotate IPs to remain concealed, so any bookmarks or shared links should always use cascadingtrust.net.
            </p>
          </div>

          {/* Continue */}
          <button
            onClick={continueToSite}
            className="w-full border border-foreground/20 hover:border-foreground hover:bg-foreground hover:text-background py-3 text-foreground transition-all text-sm uppercase tracking-wider"
          >
            Continue →
          </button>
        </div>

        {/* Right - Graph */}
        <div className="flex-shrink-0">
          {inviteData?.trees && inviteData.trees.length > 0 && (
            <TreeGraph trees={inviteData.trees} />
          )}
        </div>
      </div>
    </div>
  );
}
