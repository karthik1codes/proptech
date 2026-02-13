import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { MessageCircle, Phone, Check, X, Loader2, Send, Shield, Copy, ExternalLink, ChevronDown, ChevronUp } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { toast } from 'sonner';
import { API } from '../App';
import {
  InputOTP,
  InputOTPGroup,
  InputOTPSlot,
} from "./ui/input-otp";

// Twilio Sandbox Number from env
const TWILIO_WHATSAPP_NUMBER = "+14155238886";

export default function WhatsAppLinking() {
  const [linkingStatus, setLinkingStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [step, setStep] = useState('check'); // check, enter_phone, verify_otp, linked
  const [sending, setSending] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [showAllCommands, setShowAllCommands] = useState(false);

  useEffect(() => {
    checkLinkingStatus();
  }, []);

  const checkLinkingStatus = async () => {
    try {
      const response = await axios.get(`${API}/whatsapp/link/status`, { withCredentials: true });
      setLinkingStatus(response.data);
      
      if (response.data.linked) {
        setStep('linked');
        setPhoneNumber(response.data.phone_number || '');
      } else {
        setStep('enter_phone');
      }
    } catch (error) {
      console.error('Error checking linking status:', error);
      setStep('enter_phone');
    } finally {
      setLoading(false);
    }
  };

  const initiateLink = async () => {
    if (!phoneNumber || !phoneNumber.startsWith('+')) {
      toast.error('Please enter a valid phone number starting with +');
      return;
    }

    setSending(true);
    try {
      const response = await axios.post(
        `${API}/whatsapp/link/initiate`,
        { phone_number: phoneNumber },
        { withCredentials: true }
      );
      
      toast.success('Verification code sent to your WhatsApp!');
      setStep('verify_otp');
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'Failed to send verification code';
      toast.error(errorMsg);
    } finally {
      setSending(false);
    }
  };

  const verifyOtp = async () => {
    if (otpCode.length !== 6) {
      toast.error('Please enter the 6-digit code');
      return;
    }

    setVerifying(true);
    try {
      const response = await axios.post(
        `${API}/whatsapp/link/verify`,
        { phone_number: phoneNumber, otp_code: otpCode },
        { withCredentials: true }
      );
      
      toast.success('WhatsApp linked successfully!');
      setStep('linked');
      setLinkingStatus({ linked: true, phone_number: phoneNumber });
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'Verification failed';
      toast.error(errorMsg);
    } finally {
      setVerifying(false);
    }
  };

  const unlinkPhone = async () => {
    try {
      await axios.post(`${API}/whatsapp/link/unlink`, {}, { withCredentials: true });
      toast.success('WhatsApp unlinked');
      setStep('enter_phone');
      setPhoneNumber('');
      setOtpCode('');
      setLinkingStatus(null);
    } catch (error) {
      toast.error('Failed to unlink WhatsApp');
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard!');
  };

  const openWhatsApp = () => {
    window.open(`https://wa.me/${TWILIO_WHATSAPP_NUMBER.replace('+', '')}`, '_blank');
  };

  if (loading) {
    return (
      <Card className="glass border-white/5">
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-cyan-400" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="glass border-white/5 glow-primary" data-testid="whatsapp-linking">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-gradient-to-br from-green-500/20 to-emerald-500/20 border border-green-500/20">
              <MessageCircle className="w-5 h-5 text-green-400" />
            </div>
            <div>
              <CardTitle className="text-lg text-white">Infranomic WhatsApp Bot</CardTitle>
              <CardDescription className="text-slate-400">
                Control your portfolio via WhatsApp messages
              </CardDescription>
            </div>
          </div>
          {step === 'linked' && (
            <Badge className="bg-green-500/20 text-green-400 border-green-500/30">
              <Check className="w-3 h-3 mr-1" /> Connected
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {step === 'enter_phone' && (
          <>
            <div className="p-4 rounded-xl bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-white/5">
              <p className="text-sm text-slate-300 mb-4">
                Link your WhatsApp to control floors, run simulations, and receive alerts directly from your phone.
              </p>
              
              <div className="space-y-3">
                <label className="text-sm text-slate-400">Phone Number (E.164 format)</label>
                <div className="flex gap-2">
                  <Input
                    type="tel"
                    placeholder="+91 98765 43210"
                    value={phoneNumber}
                    onChange={(e) => setPhoneNumber(e.target.value)}
                    className="flex-1 bg-slate-800/50 border-white/10 text-white placeholder:text-slate-500"
                    data-testid="phone-input"
                  />
                  <Button
                    onClick={initiateLink}
                    disabled={sending || !phoneNumber}
                    className="bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-400 hover:to-emerald-500 text-white"
                    data-testid="send-otp-btn"
                  >
                    {sending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <>
                        <Send className="w-4 h-4 mr-2" />
                        Send Code
                      </>
                    )}
                  </Button>
                </div>
                <p className="text-xs text-slate-500">
                  Example: +919876543210 or +14155238886
                </p>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
              <p className="text-xs text-amber-300 flex items-start gap-2">
                <Shield className="w-4 h-4 mt-0.5 shrink-0" />
                <span>
                  First, join the Twilio Sandbox: Send <strong>"join &lt;sandbox-code&gt;"</strong> to <strong>+1 415 523 8886</strong> on WhatsApp
                </span>
              </p>
            </div>
          </>
        )}

        {step === 'verify_otp' && (
          <>
            <div className="p-4 rounded-xl bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-white/5">
              <p className="text-sm text-slate-300 mb-4">
                Enter the 6-digit code sent to <strong className="text-cyan-400">{phoneNumber}</strong>
              </p>
              
              <div className="flex flex-col items-center gap-4">
                <InputOTP
                  maxLength={6}
                  value={otpCode}
                  onChange={(value) => setOtpCode(value)}
                  data-testid="otp-input"
                >
                  <InputOTPGroup>
                    <InputOTPSlot index={0} className="bg-slate-800/50 border-white/10 text-white text-xl" />
                    <InputOTPSlot index={1} className="bg-slate-800/50 border-white/10 text-white text-xl" />
                    <InputOTPSlot index={2} className="bg-slate-800/50 border-white/10 text-white text-xl" />
                    <InputOTPSlot index={3} className="bg-slate-800/50 border-white/10 text-white text-xl" />
                    <InputOTPSlot index={4} className="bg-slate-800/50 border-white/10 text-white text-xl" />
                    <InputOTPSlot index={5} className="bg-slate-800/50 border-white/10 text-white text-xl" />
                  </InputOTPGroup>
                </InputOTP>

                <div className="flex gap-2 w-full">
                  <Button
                    variant="outline"
                    onClick={() => setStep('enter_phone')}
                    className="flex-1 border-white/10 text-slate-300 hover:bg-white/5"
                  >
                    Back
                  </Button>
                  <Button
                    onClick={verifyOtp}
                    disabled={verifying || otpCode.length !== 6}
                    className="flex-1 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-400 hover:to-emerald-500 text-white"
                    data-testid="verify-otp-btn"
                  >
                    {verifying ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <>
                        <Check className="w-4 h-4 mr-2" />
                        Verify
                      </>
                    )}
                  </Button>
                </div>
              </div>

              <p className="text-xs text-slate-500 text-center mt-3">
                Code expires in 10 minutes
              </p>
            </div>
          </>
        )}

        {step === 'linked' && (
          <>
            <div className="p-4 rounded-xl bg-gradient-to-br from-green-500/10 to-emerald-500/10 border border-green-500/20">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 rounded-full bg-green-500/20">
                  <Phone className="w-4 h-4 text-green-400" />
                </div>
                <div>
                  <p className="text-sm font-medium text-white">{linkingStatus?.phone_number}</p>
                  <p className="text-xs text-slate-400">WhatsApp Connected</p>
                </div>
              </div>

              <div className="space-y-3 text-sm">
                <p className="text-slate-300 font-medium">Quick Commands:</p>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="p-2 rounded bg-white/5 text-slate-400">
                    <span className="text-cyan-400">list</span> - All properties
                  </div>
                  <div className="p-2 rounded bg-white/5 text-slate-400">
                    <span className="text-cyan-400">Horizon</span> - Property details
                  </div>
                  <div className="p-2 rounded bg-white/5 text-slate-400">
                    <span className="text-cyan-400">close F3 in Horizon</span>
                  </div>
                  <div className="p-2 rounded bg-white/5 text-slate-400">
                    <span className="text-cyan-400">simulate closing F2</span>
                  </div>
                </div>
                
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowAllCommands(!showAllCommands)}
                  className="w-full text-cyan-400 hover:text-cyan-300 hover:bg-white/5"
                >
                  {showAllCommands ? (
                    <>
                      <ChevronUp className="w-4 h-4 mr-2" />
                      Hide All Commands
                    </>
                  ) : (
                    <>
                      <ChevronDown className="w-4 h-4 mr-2" />
                      Show All Commands
                    </>
                  )}
                </Button>

                {showAllCommands && (
                  <div className="space-y-3 pt-2 border-t border-white/10">
                    {/* Property Analytics */}
                    <div>
                      <p className="text-xs text-slate-500 uppercase mb-2">Property Analytics</p>
                      <div className="grid grid-cols-1 gap-1 text-xs">
                        <div className="p-2 rounded bg-white/5 text-slate-400">
                          <span className="text-cyan-400">list</span> - Show all properties
                        </div>
                        <div className="p-2 rounded bg-white/5 text-slate-400">
                          <span className="text-cyan-400">overview</span> - Portfolio summary
                        </div>
                        <div className="p-2 rounded bg-white/5 text-slate-400">
                          <span className="text-cyan-400">portfolio</span> - All properties benchmarks
                        </div>
                      </div>
                    </div>

                    {/* Floor Control */}
                    <div>
                      <p className="text-xs text-slate-500 uppercase mb-2">Floor Control</p>
                      <div className="grid grid-cols-1 gap-1 text-xs">
                        <div className="p-2 rounded bg-white/5 text-slate-400">
                          <span className="text-cyan-400">close floor 7 in Horizon</span>
                        </div>
                        <div className="p-2 rounded bg-white/5 text-slate-400">
                          <span className="text-cyan-400">close floors 2,4,5</span>
                        </div>
                        <div className="p-2 rounded bg-white/5 text-slate-400">
                          <span className="text-cyan-400">open floor 3</span>
                        </div>
                        <div className="p-2 rounded bg-white/5 text-slate-400">
                          <span className="text-cyan-400">reset Horizon</span> / <span className="text-cyan-400">reset all</span>
                        </div>
                      </div>
                    </div>

                    {/* Simulation */}
                    <div>
                      <p className="text-xs text-slate-500 uppercase mb-2">Simulation</p>
                      <div className="grid grid-cols-1 gap-1 text-xs">
                        <div className="p-2 rounded bg-white/5 text-slate-400">
                          <span className="text-cyan-400">simulate closing F3</span>
                        </div>
                        <div className="p-2 rounded bg-white/5 text-slate-400">
                          <span className="text-cyan-400">what if we close floor 2?</span>
                        </div>
                        <div className="p-2 rounded bg-white/5 text-slate-400">
                          <span className="text-cyan-400">run optimization</span>
                        </div>
                      </div>
                    </div>

                    {/* Reports & AI */}
                    <div>
                      <p className="text-xs text-slate-500 uppercase mb-2">Reports & AI</p>
                      <div className="grid grid-cols-1 gap-1 text-xs">
                        <div className="p-2 rounded bg-white/5 text-slate-400">
                          <span className="text-cyan-400">download PDF</span> - Executive report
                        </div>
                        <div className="p-2 rounded bg-white/5 text-slate-400">
                          <span className="text-cyan-400">energy report</span>
                        </div>
                        <div className="p-2 rounded bg-white/5 text-slate-400">
                          <span className="text-cyan-400">recommend</span> / <span className="text-cyan-400">tips</span>
                        </div>
                      </div>
                    </div>

                    {/* Alerts */}
                    <div>
                      <p className="text-xs text-slate-500 uppercase mb-2">Alerts</p>
                      <div className="grid grid-cols-1 gap-1 text-xs">
                        <div className="p-2 rounded bg-white/5 text-slate-400">
                          <span className="text-cyan-400">alerts</span> - View active alerts
                        </div>
                        <div className="p-2 rounded bg-white/5 text-slate-400">
                          <span className="text-cyan-400">subscribe</span> / <span className="text-cyan-400">unsubscribe</span>
                        </div>
                      </div>
                    </div>

                    {/* System */}
                    <div>
                      <p className="text-xs text-slate-500 uppercase mb-2">System</p>
                      <div className="grid grid-cols-1 gap-1 text-xs">
                        <div className="p-2 rounded bg-white/5 text-slate-400">
                          <span className="text-cyan-400">help</span> - Show all commands
                        </div>
                        <div className="p-2 rounded bg-white/5 text-slate-400">
                          <span className="text-cyan-400">status</span> - System status
                        </div>
                        <div className="p-2 rounded bg-white/5 text-slate-400">
                          <span className="text-cyan-400">undo</span> - Revert last change
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="flex gap-2">
              <Button
                onClick={openWhatsApp}
                className="flex-1 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-400 hover:to-emerald-500 text-white"
              >
                <ExternalLink className="w-4 h-4 mr-2" />
                Open WhatsApp
              </Button>
              <Button
                variant="outline"
                onClick={unlinkPhone}
                className="border-red-500/30 text-red-400 hover:bg-red-500/10"
                data-testid="unlink-btn"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
          </>
        )}

        {/* WhatsApp number to message */}
        <div className="p-3 rounded-lg bg-slate-800/30 border border-white/5">
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-400">
              Send messages to: <strong className="text-green-400">{TWILIO_WHATSAPP_NUMBER}</strong>
            </p>
            <div className="flex gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => copyToClipboard(TWILIO_WHATSAPP_NUMBER)}
                className="h-6 px-2 text-slate-400 hover:text-white hover:bg-white/10"
              >
                <Copy className="w-3 h-3" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={openWhatsApp}
                className="h-6 px-2 text-green-400 hover:text-green-300 hover:bg-white/10"
              >
                <ExternalLink className="w-3 h-3" />
              </Button>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
