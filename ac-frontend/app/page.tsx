import { title } from "process";
import React from "react";


const HomePage: React.FC = () => {
  return (
    <main style={styles.container}>
      <h1 style={styles.title}>AC Access Control System</h1>
      <p>This is your awesome React + TypeScript homepage.</p>
    </main>
  );
};

const styles = {
  container: {
    maxWidth: "800px",
    margin: "0 auto",
    padding: "2rem",
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
  },
  heading: {
    fontSize: "2.5rem",
    marginBottom: "1rem",
  },
  paragraph: {
    fontSize: "1.2rem",
    lineHeight: 1.6,
  },
  navList: {
    listStyleType: "none" as const,
    padding: 0,
  },
  navItem: {
    marginBottom: "0.5rem",
  },
  navLink: {
    color: "#0070f3",
    textDecoration: "none",
  },
  title: {
    color: "#911486ff",
    fontSize: "2.5rem",
    marginBottom: "1rem",
  },
 
};  

export default HomePage;
