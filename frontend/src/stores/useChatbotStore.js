import { create } from 'zustand';
import { generateResponse, getQuickQuestions } from '../utils/chatbotEngine';

const useChatbotStore = create((set, get) => ({
  isOpen: false,
  messages: [
    {
      id: 'welcome',
      role: 'bot',
      text: '您好！我是農產助手，有任何關於農產品價格、趨勢、預測的問題都可以問我。',
      timestamp: Date.now(),
    },
  ],
  quickQuestions: getQuickQuestions(),

  toggle: () => set((s) => ({ isOpen: !s.isOpen })),
  open: () => set({ isOpen: true }),
  close: () => set({ isOpen: false }),

  addUserMessage: (text, context = {}) => {
    const userMsg = {
      id: `user-${Date.now()}`,
      role: 'user',
      text,
      timestamp: Date.now(),
    };

    const reply = generateResponse(text, context);
    const botMsg = {
      id: `bot-${Date.now()}`,
      role: 'bot',
      text: reply,
      timestamp: Date.now() + 1,
    };

    set((s) => ({
      messages: [...s.messages, userMsg, botMsg],
    }));
  },

  clearMessages: () =>
    set({
      messages: [
        {
          id: 'welcome',
          role: 'bot',
          text: '您好！我是農產助手，有任何關於農產品價格、趨勢、預測的問題都可以問我。',
          timestamp: Date.now(),
        },
      ],
    }),
}));

export default useChatbotStore;
