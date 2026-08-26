import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { TaskTable } from "./TaskTable";
import { useAppStore } from "../stores/appStore";

describe("TaskTable", () => {
  beforeEach(() => {
    useAppStore.setState({ tasks: {} });
  });

  it("shows an empty state", () => {
    render(<TaskTable />);
    expect(screen.getByText("下载任务会显示在这里")).toBeInTheDocument();
  });

  it("renders task progress", () => {
    useAppStore.setState({
      tasks: {
        demo: {
          id: "demo",
          url: "https://youtu.be/demo",
          title: "示例视频",
          outputDir: "C:\\Downloads",
          formatId: "best",
          status: "downloading",
          progress: 42.5,
          speed: "2.1 MiB/s",
          createdAt: "2026-08-26T00:00:00Z",
        },
      },
    });
    render(<TaskTable />);
    expect(screen.getByText("示例视频")).toBeInTheDocument();
    expect(screen.getByText("42.5%")).toBeInTheDocument();
    expect(screen.getByText("2.1 MiB/s")).toBeInTheDocument();
    expect(screen.getByText("正在处理 1 个下载任务")).toBeInTheDocument();
  });

  it("shows an open-directory action for completed downloads", () => {
    useAppStore.setState({
      tasks: {
        complete: {
          id: "complete",
          url: "https://youtu.be/complete",
          title: "已完成视频",
          outputDir: "C:\\Downloads",
          formatId: "best",
          status: "completed",
          progress: 100,
          createdAt: "2026-08-26T00:00:00Z",
        },
      },
    });

    render(<TaskTable />);
    expect(screen.getByRole("button", { name: "打开目录" })).toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});
