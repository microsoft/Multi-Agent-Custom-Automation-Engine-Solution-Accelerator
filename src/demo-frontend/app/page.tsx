'use client';

import React, { useState, useCallback, useMemo } from 'react';
import StatsCards, { StatsData } from '@/components/StatsCards';
import AppointmentCalendar, { Appointment } from '@/components/AppointmentCalendar';
import CallButton, { CallState, CallEvent } from '@/components/CallButton';
import ChatInterface, { ChatMessage } from '@/components/ChatInterface';

/**
 * Dashboard section wrapper with consistent styling
 */
const DashboardSection: React.FC<{
  title?: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
}> = ({ title, description, children, className = '' }) => (
  <section className={`space-y-3 ${className}`}>
    {(title || description) && (
      <div className="space-y-1">
        {title && (
          <h2 className="text-lg font-semibold text-foreground">{title}</h2>
        )}
        {description && (
          <p className="text-sm text-muted-foreground">{description}</p>
        )}
      </div>
    )}
    {children}
  </section>
);

/**
 * AI Assistant icon for feature highlight
 */
const AIAssistantIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    className="h-8 w-8"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M12 8V4H8" />
    <rect width="16" height="12" x="4" y="8" rx="2" />
    <path d="M2 14h2" />
    <path d="M20 14h2" />
    <path d="M15 13v2" />
    <path d="M9 13v2" />
  </svg>
);

/**
 * Mock stats data generator based on appointments
 */
function calculateStatsFromAppointments(appointments: Appointment[]): StatsData {
  const confirmed = appointments.filter((apt) => apt.status === 'confirmed').length;
  const pending = appointments.filter((apt) => apt.status === 'pending').length;
  const scheduled = confirmed + pending;
  // Estimate revenue based on number of appointments (demo purposes)
  const avgAppointmentValue = 150;
  const revenue = confirmed * avgAppointmentValue;

  return {
    scheduled,
    confirmed,
    pending,
    revenue,
  };
}

/**
 * Generate mock appointments relative to today's date
 */
function generateMockAppointments(): Appointment[] {
  const toLocalDateString = (date: Date): string => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  const getDateString = (daysFromToday: number): string => {
    const date = new Date();
    date.setDate(date.getDate() + daysFromToday);
    return toLocalDateString(date);
  };

  return [
    {
      id: '1',
      clientName: 'John Smith',
      service: 'Consultation',
      date: getDateString(0),
      startTime: '09:00',
      endTime: '09:30',
      status: 'confirmed',
      phone: '(555) 123-4567',
    },
    {
      id: '2',
      clientName: 'Sarah Johnson',
      service: 'Follow-up',
      date: getDateString(0),
      startTime: '10:30',
      endTime: '11:00',
      status: 'confirmed',
    },
    {
      id: '3',
      clientName: 'Mike Davis',
      service: 'Initial Visit',
      date: getDateString(0),
      startTime: '14:00',
      endTime: '15:00',
      status: 'pending',
      phone: '(555) 987-6543',
    },
    {
      id: '4',
      clientName: 'Emily Brown',
      service: 'Checkup',
      date: getDateString(1),
      startTime: '11:00',
      endTime: '11:30',
      status: 'confirmed',
    },
    {
      id: '5',
      clientName: 'David Wilson',
      service: 'Emergency',
      date: getDateString(1),
      startTime: '15:30',
      endTime: '16:30',
      status: 'pending',
      notes: 'Urgent appointment',
    },
    {
      id: '6',
      clientName: 'Lisa Anderson',
      service: 'Consultation',
      date: getDateString(2),
      startTime: '09:30',
      endTime: '10:00',
      status: 'confirmed',
    },
    {
      id: '7',
      clientName: 'Robert Taylor',
      service: 'Service A',
      date: getDateString(2),
      startTime: '13:00',
      endTime: '14:00',
      status: 'cancelled',
    },
    {
      id: '8',
      clientName: 'Jennifer Martinez',
      service: 'Follow-up',
      date: getDateString(3),
      startTime: '10:00',
      endTime: '10:30',
      status: 'confirmed',
    },
    {
      id: '9',
      clientName: 'Chris Lee',
      service: 'Initial Visit',
      date: getDateString(4),
      startTime: '14:30',
      endTime: '15:30',
      status: 'pending',
    },
    {
      id: '10',
      clientName: 'Amanda White',
      service: 'Consultation',
      date: getDateString(5),
      startTime: '11:30',
      endTime: '12:00',
      status: 'confirmed',
    },
  ];
}

/**
 * Main Dashboard Page
 *
 * Composes all dashboard components:
 * - StatsCards: Key metrics overview
 * - AppointmentCalendar: Weekly/monthly appointment view
 * - CallButton: Click-to-call with AI assistant
 * - ChatInterface: Text-based chat with AI assistant
 *
 * This is the entry point for the demo frontend, showcasing
 * the AI appointment assistant capabilities to prospects.
 */
export default function DashboardPage() {
  // State
  const [appointments] = useState<Appointment[]>(generateMockAppointments);
  const [selectedAppointment, setSelectedAppointment] = useState<Appointment | null>(null);
  const [callState, setCallState] = useState<CallState>('idle');
  const [isLoading, setIsLoading] = useState(false);

  // Calculate stats from appointments
  const stats = useMemo(
    () => calculateStatsFromAppointments(appointments),
    [appointments]
  );

  /**
   * Handle appointment click - show details
   */
  const handleAppointmentClick = useCallback((appointment: Appointment) => {
    setSelectedAppointment(appointment);
  }, []);

  /**
   * Handle call state changes
   */
  const handleCallStateChange = useCallback((state: CallState) => {
    setCallState(state);
  }, []);

  /**
   * Handle call events (for logging/analytics)
   */
  const handleCallEvent = useCallback((event: CallEvent) => {
    // In production, this would send events to analytics
    if (event.type === 'transcript' && event.transcript) {
      // Could display transcripts in real-time
    }
  }, []);

  /**
   * Handle chat message sending
   * In production, this connects to the AI backend
   */
  const handleSendMessage = useCallback(
    async function* (
      input: string,
      _history: ChatMessage[]
    ): AsyncGenerator<string> {
      // Simulate AI response with streaming
      const responses = [
        "Hello! I'm your AI appointment assistant. ",
        "I can help you schedule appointments, ",
        "answer questions about our services, ",
        "or connect you with our team. ",
        "How can I assist you today?",
      ];

      // Simulate typing delay
      for (const chunk of responses) {
        await new Promise((resolve) => setTimeout(resolve, 200));
        yield chunk;
      }
    },
    []
  );

  /**
   * Close appointment detail modal
   */
  const closeAppointmentDetail = useCallback(() => {
    setSelectedAppointment(null);
  }, []);

  return (
    <div className="container mx-auto px-4 py-8 space-y-8">
      {/* Hero/Welcome Section */}
      <section className="text-center space-y-4 py-6">
        <div className="inline-flex items-center justify-center p-3 bg-brand/10 rounded-full text-brand">
          <AIAssistantIcon />
        </div>
        <h1 className="text-3xl font-bold text-foreground">
          AI Appointment Assistant Demo
        </h1>
        <p className="text-muted-foreground max-w-2xl mx-auto">
          Experience how our AI assistant can handle your appointment scheduling,
          answer customer questions, and manage your calendar 24/7.
        </p>
      </section>

      {/* Stats Overview */}
      <DashboardSection
        title="Dashboard Overview"
        description="Your appointment metrics at a glance"
      >
        <StatsCards stats={stats} loading={isLoading} />
      </DashboardSection>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Calendar Section - Takes 2 columns on large screens */}
        <div className="lg:col-span-2">
          <DashboardSection
            title="Appointment Calendar"
            description="View and manage scheduled appointments"
          >
            <AppointmentCalendar
              appointments={appointments}
              initialView="week"
              loading={isLoading}
              onAppointmentClick={handleAppointmentClick}
            />
          </DashboardSection>
        </div>

        {/* Right Sidebar - Contact & Chat */}
        <div className="space-y-8">
          {/* Call Button Section */}
          <DashboardSection
            title="Talk to AI Assistant"
            description="Call to experience the voice assistant"
          >
            <div className="card p-6 text-center space-y-4">
              <p className="text-sm text-muted-foreground">
                Click below to start a demo call with our AI appointment assistant.
                It can answer questions about your business and book appointments.
              </p>
              <CallButton
                size="lg"
                label="Start Demo Call"
                onCallStateChange={handleCallStateChange}
                onCallEvent={handleCallEvent}
                className="w-full justify-center"
              />
              {callState === 'connected' && (
                <p className="text-xs text-green-600">
                  Call connected! Try asking about available appointments.
                </p>
              )}
            </div>
          </DashboardSection>

          {/* Chat Interface Section */}
          <DashboardSection
            title="Chat with AI"
            description="Text-based conversation with the assistant"
          >
            <ChatInterface
              onSendMessage={handleSendMessage}
              placeholder="Ask about appointments, services, or hours..."
              welcomeMessage="Hi! I'm your AI assistant. I can help you schedule appointments, answer questions about services, or provide information about the business."
              maxHeight="450px"
            />
          </DashboardSection>
        </div>
      </div>

      {/* Features Highlight Section */}
      <section className="border-t border-border pt-8 mt-8">
        <h2 className="text-xl font-semibold text-foreground text-center mb-6">
          What This AI Assistant Can Do
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <FeatureCard
            icon={
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-6 w-6"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <rect width="18" height="18" x="3" y="4" rx="2" ry="2" />
                <line x1="16" x2="16" y1="2" y2="6" />
                <line x1="8" x2="8" y1="2" y2="6" />
                <line x1="3" x2="21" y1="10" y2="10" />
              </svg>
            }
            title="24/7 Scheduling"
            description="Book appointments any time, even after hours"
          />
          <FeatureCard
            icon={
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-6 w-6"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
              </svg>
            }
            title="Voice Calls"
            description="Natural conversations via phone calls"
          />
          <FeatureCard
            icon={
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-6 w-6"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
            }
            title="Instant Answers"
            description="Answer common questions about your business"
          />
          <FeatureCard
            icon={
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-6 w-6"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                <path d="M16 3.13a4 4 0 0 1 0 7.75" />
              </svg>
            }
            title="Lead Capture"
            description="Collect customer info and follow up"
          />
        </div>
      </section>

      {/* Appointment Detail Modal */}
      {selectedAppointment && (
        <AppointmentDetailModal
          appointment={selectedAppointment}
          onClose={closeAppointmentDetail}
        />
      )}
    </div>
  );
}

/**
 * Feature card component for highlighting capabilities
 */
const FeatureCard: React.FC<{
  icon: React.ReactNode;
  title: string;
  description: string;
}> = ({ icon, title, description }) => (
  <div className="card p-6 text-center hover:shadow-md transition-shadow">
    <div className="inline-flex items-center justify-center p-3 bg-brand/10 rounded-lg text-brand mb-4">
      {icon}
    </div>
    <h3 className="font-semibold text-foreground mb-2">{title}</h3>
    <p className="text-sm text-muted-foreground">{description}</p>
  </div>
);

/**
 * Appointment detail modal component
 */
const AppointmentDetailModal: React.FC<{
  appointment: Appointment;
  onClose: () => void;
}> = ({ appointment, onClose }) => {
  const formatTime = (time: string): string => {
    const [hours, minutes] = time.split(':').map(Number);
    const period = hours >= 12 ? 'PM' : 'AM';
    const displayHours = hours % 12 || 12;
    return `${displayHours}:${minutes.toString().padStart(2, '0')} ${period}`;
  };

  const parseLocalDate = (dateString: string): Date => {
    const [yearStr, monthStr, dayStr] = dateString.split('-');
    const year = Number(yearStr);
    const month = Number(monthStr);
    const day = Number(dayStr);
    if (!year || !month || !day) {
      return new Date(dateString);
    }
    return new Date(year, month - 1, day);
  };

  const formatDate = (dateString: string): string => {
    const date = parseLocalDate(dateString);
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const statusColors = {
    confirmed: 'bg-green-100 text-green-700',
    pending: 'bg-amber-100 text-amber-700',
    cancelled: 'bg-red-100 text-red-700',
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="appointment-modal-title"
    >
      <div
        className="bg-background rounded-xl shadow-xl max-w-md w-full mx-4 p-6"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3
              id="appointment-modal-title"
              className="text-lg font-semibold text-foreground"
            >
              {appointment.clientName}
            </h3>
            <p className="text-sm text-muted-foreground">{appointment.service}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 hover:bg-muted rounded-lg transition-colors"
            aria-label="Close modal"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-5 w-5 text-muted-foreground"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" x2="6" y1="6" y2="18" />
              <line x1="6" x2="18" y1="6" y2="18" />
            </svg>
          </button>
        </div>

        {/* Status Badge */}
        <div className="mb-4">
          <span
            className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium capitalize ${
              statusColors[appointment.status]
            }`}
          >
            {appointment.status}
          </span>
        </div>

        {/* Details */}
        <div className="space-y-3 mb-6">
          <div className="flex items-center gap-3 text-sm">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-5 w-5 text-muted-foreground"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect width="18" height="18" x="3" y="4" rx="2" ry="2" />
              <line x1="16" x2="16" y1="2" y2="6" />
              <line x1="8" x2="8" y1="2" y2="6" />
              <line x1="3" x2="21" y1="10" y2="10" />
            </svg>
            <span>{formatDate(appointment.date)}</span>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-5 w-5 text-muted-foreground"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            <span>
              {formatTime(appointment.startTime)} - {formatTime(appointment.endTime)}
            </span>
          </div>
          {appointment.phone && (
            <div className="flex items-center gap-3 text-sm">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-5 w-5 text-muted-foreground"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
              </svg>
              <a
                href={`tel:${appointment.phone}`}
                className="text-brand hover:underline"
              >
                {appointment.phone}
              </a>
            </div>
          )}
          {appointment.notes && (
            <div className="flex items-start gap-3 text-sm">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-5 w-5 text-muted-foreground flex-shrink-0 mt-0.5"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" x2="8" y1="13" y2="13" />
                <line x1="16" x2="8" y1="17" y2="17" />
                <polyline points="10 9 9 9 8 9" />
              </svg>
              <span className="text-muted-foreground">{appointment.notes}</span>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 px-4 py-2 bg-muted hover:bg-muted/80 text-foreground rounded-lg font-medium transition-colors"
          >
            Close
          </button>
          {appointment.status !== 'cancelled' && (
            <button
              type="button"
              className="flex-1 px-4 py-2 bg-brand hover:bg-brand-dark text-white rounded-lg font-medium transition-colors"
            >
              Reschedule
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
