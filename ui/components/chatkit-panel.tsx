"use client";

import { ChatKit, useChatKit } from "@openai/chatkit-react";
import React from "react";

type ChatKitPanelProps = {
  initialThreadId?: string | null;
  onThreadChange?: (threadId: string | null) => void;
  onResponseEnd?: () => void;
  onRunnerUpdate?: () => void;
  onRunnerEventDelta?: (events: any[]) => void;
  onRunnerBindThread?: (threadId: string) => void;
};

const CHATKIT_DOMAIN_KEY =
  process.env.NEXT_PUBLIC_CHATKIT_DOMAIN_KEY ?? "domain_pk_localhost_dev";

export function ChatKitPanel({
  initialThreadId,
  onThreadChange,
  onResponseEnd,
  onRunnerUpdate,
  onRunnerEventDelta,
  onRunnerBindThread,
}: ChatKitPanelProps) {
  const chatkit = useChatKit({
    api: {
      url: "/chatkit",
      domainKey: CHATKIT_DOMAIN_KEY,
    },
    composer: {
      placeholder: "Escribe tu mensaje...",
    },
    history: {
      enabled: false,
    },
    theme: {
      colorScheme: "light",
      radius: "round",
      density: "normal",
      color: {
        accent: {
          primary: "#2563eb",
          level: 1,
        },
      },
    },
    initialThread: initialThreadId ?? null,
    startScreen: {
      greeting: "¡Hola! Soy tu asistente de Aerolíneas Istmeñas. ¿En qué te puedo ayudar hoy?",
      prompts: [
        { label: "Cambiar mi asiento", prompt: "¿Me puedes mover al asiento 14C?" },
        {
          label: "Estado de vuelo",
          prompt: "¿Cuál es el estado del vuelo IS-123?",
        },
        {
          label: "Conexión perdida",
          prompt:
            "Mi vuelo de David a Ciudad de Panamá se retrasó y perdí mi conexión a Cartagena. Además, mi equipaje facturado no aparece y necesito pasar la noche en la ciudad. ¿Me pueden ayudar?",
        },
      ],
    },
    threadItemActions: {
      feedback: false,
    },
    onThreadChange: ({ threadId }) => onThreadChange?.(threadId ?? null),
    onResponseEnd: () => onResponseEnd?.(),
    onError: ({ error }) => {
      console.error("ChatKit error", error);
    },
    onEffect: async ({ name }) => {
      if (name === "runner_state_update") {
        onRunnerUpdate?.();
      }
      if (name === "runner_event_delta") {
        onRunnerEventDelta?.((arguments as any)?.[0]?.data?.events ?? []);
      }
      if (name === "runner_bind_thread") {
        const tid = (arguments as any)?.[0]?.data?.thread_id;
        if (tid) {
          onRunnerBindThread?.(tid);
        }
      }
    },
  });

  return (
    <div className="flex flex-col h-full flex-1 bg-white shadow-sm border border-gray-200 border-t-0 rounded-xl">
      <div className="bg-blue-600 text-white h-12 px-4 flex items-center rounded-t-xl">
        <h2 className="font-semibold text-sm sm:text-base lg:text-lg">
          Vista del Cliente
        </h2>
      </div>
      <div className="flex-1 overflow-hidden pb-1.5">
        <ChatKit
          control={chatkit.control}
          className="block h-full w-full"
          style={{ height: "100%", width: "100%" }}
        />
      </div>
    </div>
  );
}
