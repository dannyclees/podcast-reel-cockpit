// frame_scan.swift: faces and on-screen text in every frame of a finished Short (rule R23). Apple Vision, on-device, free.
// build: swiftc -O pipeline/frame_scan.swift -o bin/frame_scan
// usage: frame_scan <video> <out.json> [fps, default 30 = every frame]
// Output: {"w","h","dur","fps","frames":[{"t","faces":[[x0,y0,x1,y1]...],"text":[{"s":"...","box":[x0,y0,x1,y1]}...]}]}
// Boxes are 0..1 from the top-left.
import AVFoundation
import Vision
import Foundation

let args = CommandLine.arguments
guard args.count >= 3 else { print("usage: frame_scan <video> <out.json> [fps]"); exit(2) }
let url = URL(fileURLWithPath: args[1])
let fps = args.count > 3 ? Double(args[3]) ?? 30 : 30
let asset = AVURLAsset(url: url)
let sem = DispatchSemaphore(value: 0)
var dur = 0.0
var size = CGSize.zero
Task {
    dur = (try? await asset.load(.duration).seconds) ?? 0
    if let tr = try? await asset.loadTracks(withMediaType: .video).first {
        let s = (try? await tr.load(.naturalSize)) ?? .zero
        let t = (try? await tr.load(.preferredTransform)) ?? .identity
        let r = CGRect(origin: .zero, size: s).applying(t)
        size = CGSize(width: abs(r.width), height: abs(r.height))
    }
    sem.signal()
}
sem.wait()
let gen = AVAssetImageGenerator(asset: asset)
gen.appliesPreferredTrackTransform = true
gen.requestedTimeToleranceBefore = .zero
gen.requestedTimeToleranceAfter = .zero
gen.maximumSize = CGSize(width: 540, height: 960)

func box(_ r: CGRect) -> [Double] {   // Vision is bottom-left origin; flip to top-left
    [Double(r.minX), Double(1 - r.maxY), Double(r.maxX), Double(1 - r.minY)].map { ($0 * 1000).rounded() / 1000 }
}

var frames: [[String: Any]] = []
var t = 0.0
while t < dur - 0.001 {
    var row: [String: Any] = ["t": (t * 1000).rounded() / 1000]
    if let img = try? gen.copyCGImage(at: CMTime(seconds: t, preferredTimescale: 600), actualTime: nil) {
        let fq = VNDetectFaceRectanglesRequest()
        let tq = VNRecognizeTextRequest(); tq.recognitionLevel = .fast; tq.usesLanguageCorrection = false
        let h = VNImageRequestHandler(cgImage: img, options: [:])
        try? h.perform([fq, tq])
        row["faces"] = (fq.results ?? []).map { box($0.boundingBox) }
        row["text"] = (tq.results ?? []).compactMap { o -> [String: Any]? in
            guard let c = o.topCandidates(1).first else { return nil }
            return ["s": c.string, "box": box(o.boundingBox)]
        }
    }
    frames.append(row)
    t += 1.0 / fps
}
let out: [String: Any] = ["w": Double(size.width), "h": Double(size.height), "dur": dur, "fps": fps, "frames": frames]
let data = try! JSONSerialization.data(withJSONObject: out)
try! data.write(to: URL(fileURLWithPath: args[2]))
print("frame_scan: \(frames.count) frames -> \(args[2])")
