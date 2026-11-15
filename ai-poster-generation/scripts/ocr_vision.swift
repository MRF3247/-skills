#!/usr/bin/env swift
// macOS Vision OCR：读取图片中的文字（本地运行，免费快速，不经过任何云 API）
// 用法: swift ocr_vision.swift <图片路径>
// 适用: 文字密集的参考图 / 提示词截图 / 信息图 / 梗图（比 MiniMax 视觉转录准得多）
// 分工: OCR 读字，MiniMax 视觉只管审美（风格/版式/配色）
import Vision
import AppKit
import Foundation

let path = CommandLine.arguments[1]
guard let img = NSImage(contentsOfFile: path),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    print("无法读取图片")
    exit(1)
}
let req = VNRecognizeTextRequest { req, err in
    guard let obs = req.results as? [VNRecognizedTextObservation] else { return }
    for o in obs {
        if let t = o.topCandidates(1).first {
            print(t.string)
        }
    }
}
req.recognitionLevel = .accurate
req.recognitionLanguages = ["zh-Hans", "en-US"]
let handler = VNImageRequestHandler(cgImage: cg, options: [:])
try? handler.perform([req])
