// macOS Vision OCR 命令行工具（本地识别，zh-Hans + en-US）
// 用法: swift ocr_vision.swift <图片路径> [识别级别]
// 级别: accurate（默认，慢而准）| fast（快）
// 输出: 每行一个识别文本块
//
// 适用: 文字密集图（提示词截图/梗图文案/信息图/教学卡）读字
// 不适用: 审美判断（用 MiniMax vision_analyze）
import Vision
import AppKit
import Foundation

let path = CommandLine.arguments[1]
let level: VNRequestTextRecognitionLevel = (CommandLine.arguments.count > 2 && CommandLine.arguments[2] == "fast")
    ? .fast : .accurate

guard let img = NSImage(contentsOfFile: path),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    fputs("ERR: cannot load image \(path)\n", stderr)
    exit(1)
}

let request = VNRecognizeTextRequest { req, err in
    guard err == nil, let obs = req.results as? [VNRecognizedTextObservation] else {
        fputs("ERR: \(err?.localizedDescription ?? "unknown")\n", stderr)
        exit(2)
    }
    // 按 y 坐标降序（上→下），同 y 按 x 升序（左→右）
    let sorted = obs.sorted { a, b in
        let ay = a.boundingBox.midY, by = b.boundingBox.midY
        if abs(ay - by) > 0.01 { return ay > by }
        return a.boundingBox.minX < b.boundingBox.minX
    }
    for o in sorted {
        if let t = o.topCandidates(1).first?.string {
            print(t)
        }
    }
}
request.recognitionLevel = level
request.recognitionLanguages = ["zh-Hans", "en-US"]
request.usesLanguageCorrection = true

let handler = VNImageRequestHandler(cgImage: cg, options: [:])
try handler.perform([request])
