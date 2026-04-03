import React from 'react';
import '../components/Content/Chat.css';

/**
 * ChatExample - A component that mimics the conversation flow seen in the UI mockup
 */
const ChatExample: React.FC = () => {
  return (
    <div className="chat-container">
      <div className="messages-container">
        {/* System action message */}
        <div className="message system">
          <div className="system-message">
            Help me start onboarding Jessica.
          </div>
        </div>

        {/* Bot message */}
        <div className="message assistant">
          <div className="message-header">
            <div className="message-role">HR Agent</div>
            <div className="bot-tag">BOT</div>
          </div>
          <div className="message-content">
            Sounds good! Want me to start with a background check?
          </div>
          <div className="message-actions">
            <button className="action-button">👍</button>
            <button className="action-button">👎</button>
            <button className="action-button">🔄</button>
          </div>
        </div>

        {/* System action message */}
        <div className="message system">
          <div className="system-message">
            Yup!
          </div>
        </div>

        {/* Bot message */}
        <div className="message assistant">
          <div className="message-header">
            <div className="message-role">HR Agent</div>
            <div className="bot-tag">BOT</div>
          </div>
          <div className="message-content">
            You got it! I've initiated a background check and everything looks good to go— You're ready to move onto helping Jessica set up and Office 365 account. Want me to hand that over to your Manager Agent?
          </div>
          <div className="message-actions">
            <button className="action-button">👍</button>
            <button className="action-button">👎</button>
            <button className="action-button">🔄</button>
          </div>
        </div>

        {/* System action message */}
        <div className="message system">
          <div className="system-message">
            Let's skip that step for now
          </div>
        </div>

        {/* Bot message */}
        <div className="message assistant">
          <div className="message-header">
            <div className="message-role">HR Agent</div>
            <div className="bot-tag">BOT</div>
          </div>
          <div className="message-content">
            Alright, let's skip Office 365 onboarding.

            Want to move onto helping get her set up with a laptop for now? I can call your IT Agent.
          </div>
          <div className="message-actions">
            <button className="action-button">👍</button>
            <button className="action-button">👎</button>
            <button className="action-button">🔄</button>
          </div>
        </div>

        {/* System action message */}
        <div className="message system">
          <div className="system-message">
            Let's do it!
          </div>
        </div>

        {/* Bot message */}
        <div className="message assistant">
          <div className="message-header">
            <div className="message-role">IT Agent</div>
            <div className="bot-tag">BOT</div>
          </div>
          <div className="message-content">
            Nice move - okay we've set her up with a Surface Laptop 15 with a Snapdragon Elite. Given her role as a Product Manager, this should be more than enough power to get her killing it through her workflows.

            We can now move onto registering her with benefit— want me to get that going?
          </div>
          <div className="message-actions">
            <button className="action-button">👍</button>
            <button className="action-button">👎</button>
            <button className="action-button">🔄</button>
          </div>
        </div>
      </div>

      {/* Input area */}
      <div className="input-wrapper">
        <div className="input-container">
          <textarea 
            className="input-field"
            placeholder="Describe what you'd like to do or use / to reference files, people, and more"
            rows={1}
          />
          <button className="send-button">➤</button>
        </div>
        <div className="input-footer">
          <div>IT Agent and HR Agent are working together...</div>
          <div>AI-generated content may be incorrect</div>
        </div>
      </div>
    </div>
  );
};

export default ChatExample; 