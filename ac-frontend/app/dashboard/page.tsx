import React from "react";

const AdminDashboard: React.FC = () => {
  return (
    <main style={styles.container}>
      <h1 style={styles.title}>Admin Dashboard</h1>
      <p>Welcome to the admin dashboard. Here you can manage users and settings.</p>
      <section style={{ marginTop: "2rem" }}>
        <h2 style={styles.subtitle}>Quick Actions</h2>
        <button style={styles.navLink}>Add User</button>
      </section>
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
    padding: "0.5rem 1rem",
  },
  title: {
    color: "#911486ff",
    fontSize: "2.5rem",
    marginBottom: "1rem",
  },
  subtitle: {
    color: "#c561ffff",
    fontSize: "1.5rem",
    marginBottom: "1rem",
  },
};
export default AdminDashboard;
