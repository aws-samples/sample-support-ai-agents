import { useState, useRef } from "react";
import * as React from "react";
import { AppLayout, SideNavigation, SpaceBetween } from '@cloudscape-design/components';
import TopNavigation from "@cloudscape-design/components/top-navigation";
import { Authenticator } from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css';
import './aws-config';
import OptiraChatBot from './components/OptiraChatBot';

const ITEMS = [
  {
    type: "section",
    text: "ES OPTIRA Agents",
    items: [
      {
        type: "link",
        text: "Orchestrator",
        id: "orchestrator",
        href: "#/orchestrator",
      },
      {
        type: "link",
        text: "Support Case Knowledge-base (RAG) Agent",
        id: "rag-agent",
        href: "#/rag-agent",
      },
      {
        type: "link",
        text: "Support Case Query Aggregator Agent",
        id: "aggregator-agent",
        href: "#/aggregator-agent",
      },
      {
        type: "link",
        text: "Remediation Agent",
        id: "remediation-agent",
        href: "#/remediation-agent",
      },
      {
        type: "link",
        text: "Trusted Advisor Agent",
        id: "trusted-advisor-agent",
        href: "#/trusted-advisor-agent",
      },
      {
        type: "link",
        text: "Cost & Usage Insights Agent",
        id: "cost-usage-agent",
        href: "#/cost-usage-agent",
      },
      {
        type: "link",
        text: "EOL (End of Life) Agent",
        id: "eol-agent",
        href: "#/eol-agent",
      }
    ]
  }
];

const App = () => {
  const [currentPage, setCurrentPage] = useState("orchestrator");
  const [navigationOpen, setNavigationOpen] = useState(true);
  const [activeNavHref, setActiveNavHref] = useState("#/orchestrator");
  const [displayTopMenu] = useState(window.self === window.top);

  const appLayout = useRef();

  const handleNavigation = (event) => {
    const href = event.detail.href;
    setActiveNavHref(href);
    
    const agentId = href.replace("#/", "");
    setCurrentPage(agentId);
  };

  const MainApp = ({ signOut, user }) => {
    const renderContent = () => {
      return <OptiraChatBot currentAgent={currentPage} user={user} />;
    };

    return (
    <div style={{ height: "100vh" }}>
      {displayTopMenu && (
        <TopNavigation
          identity={{
            href: "#",
            title: "ES OPTIRA",
            logo: {
              src: "/optira-logo.png",
              alt: "ES OPTIRA"
            }
          }}
          utilities={[
            {
              type: "menu-dropdown",
              text: user.username,
              items: [
                { id: "signout", text: "Sign out" }
              ],
              onItemClick: ({ detail }) => {
                if (detail.id === "signout") signOut();
              }
            }
          ]}
        />
      )}
      
      <AppLayout
        ref={appLayout}
        navigationHide={true}
        content={
          <SpaceBetween direction="vertical" size="l">
            {renderContent()}
          </SpaceBetween>
        }
        toolsHide={true}
      />
    </div>
    );
  };

  return (
    <Authenticator>
      {({ signOut, user }) => <MainApp signOut={signOut} user={user} />}
    </Authenticator>
  );
};

export default App;
