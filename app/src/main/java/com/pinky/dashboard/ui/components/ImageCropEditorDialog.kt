package com.pinky.dashboard.ui.components

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageDecoder
import android.net.Uri
import android.os.Build
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.io.IOException
import kotlin.math.max
import kotlin.math.roundToInt

@Composable
fun ImageCropEditorDialog(
    imageUri: Uri,
    aspectRatio: Float,
    title: String,
    onDismiss: () -> Unit,
    onCropped: (Uri) -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var bitmap by remember(imageUri) { mutableStateOf<Bitmap?>(null) }
    var error by remember(imageUri) { mutableStateOf<String?>(null) }
    var zoom by remember(imageUri) { mutableFloatStateOf(1f) }
    var pan by remember(imageUri) { mutableStateOf(Offset.Zero) }
    var frame by remember(imageUri) { mutableStateOf(IntSize.Zero) }
    var busy by remember { mutableStateOf(false) }

    LaunchedEffect(imageUri) {
        bitmap = withContext(Dispatchers.IO) {
            try {
                if (Build.VERSION.SDK_INT >= 28) {
                    ImageDecoder.decodeBitmap(ImageDecoder.createSource(context.contentResolver, imageUri)) { d, _, _ ->
                        d.allocator = ImageDecoder.ALLOCATOR_SOFTWARE
                    }
                } else context.contentResolver.openInputStream(imageUri)?.use {
                    BitmapFactory.decodeStream(it)
                }
            } catch (e: Exception) {
                error = e.localizedMessage ?: "تعذر فتح الصورة"
                null
            }
        }
    }
    DisposableEffect(bitmap) {
        onDispose { bitmap?.takeIf { !it.isRecycled }?.recycle() }
    }

    Dialog(onDismissRequest = { if (!busy) onDismiss() }, properties = DialogProperties(usePlatformDefaultWidth = false)) {
        Surface(Modifier.fillMaxWidth(.94f), shape = RoundedCornerShape(20.dp), color = MaterialTheme.colorScheme.surface) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text(title, style = MaterialTheme.typography.titleMedium)
                Text("اسحب الصورة للتحريك واستخدم إصبعين للتكبير. الإطار يوضح الجزء الذي سيظهر في الموقع.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                val src = bitmap
                if (src == null) {
                    if (error != null) Text(error!!, color = MaterialTheme.colorScheme.error)
                    else Box(Modifier.fillMaxWidth().height(180.dp), contentAlignment = androidx.compose.ui.Alignment.Center) { CircularProgressIndicator() }
                } else {
                    BoxWithConstraints(Modifier.fillMaxWidth().heightIn(max = 410.dp).aspectRatio(aspectRatio.coerceIn(.55f, 3.2f)).clip(RoundedCornerShape(12.dp)).background(Color.Black)) {
                        Canvas(Modifier.fillMaxSize().onSizeChanged { frame = it }.pointerInput(src, zoom, pan, frame) {
                            detectTransformGestures { _, delta, factor, _ ->
                                val next = (zoom * factor).coerceIn(1f, 5f)
                                val w = frame.width.toFloat().coerceAtLeast(1f)
                                val h = frame.height.toFloat().coerceAtLeast(1f)
                                val scale = max(w / src.width, h / src.height) * next
                                val mx = ((src.width * scale - w) / 2f).coerceAtLeast(0f)
                                val my = ((src.height * scale - h) / 2f).coerceAtLeast(0f)
                                zoom = next
                                pan = Offset((pan.x + delta.x).coerceIn(-mx, mx), (pan.y + delta.y).coerceIn(-my, my))
                            }
                        }) {
                            val scale = max(size.width / src.width, size.height / src.height) * zoom
                            val dw = src.width * scale
                            val dh = src.height * scale
                            val left = (size.width - dw) / 2f + pan.x
                            val top = (size.height - dh) / 2f + pan.y
                            drawImage(src.asImageBitmap(), dstOffset = IntOffset(left.roundToInt(), top.roundToInt()), dstSize = IntSize(dw.roundToInt().coerceAtLeast(1), dh.roundToInt().coerceAtLeast(1)))
                            drawRect(Color.White, style = Stroke(2.dp.toPx()))
                        }
                    }
                    Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                        Text("التكبير", style = MaterialTheme.typography.labelMedium)
                        Slider(zoom, { next ->
                            val w = frame.width.toFloat().coerceAtLeast(1f)
                            val h = frame.height.toFloat().coerceAtLeast(1f)
                            val scale = max(w / src.width, h / src.height) * next
                            zoom = next
                            pan = Offset(pan.x.coerceIn(-((src.width * scale - w) / 2f).coerceAtLeast(0f), ((src.width * scale - w) / 2f).coerceAtLeast(0f)), pan.y.coerceIn(-((src.height * scale - h) / 2f).coerceAtLeast(0f), ((src.height * scale - h) / 2f).coerceAtLeast(0f)))
                        }, valueRange = 1f..5f, modifier = Modifier.weight(1f))
                    }
                }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = { zoom = 1f; pan = Offset.Zero }, enabled = src != null && !busy, modifier = Modifier.weight(1f)) { Text("إعادة ضبط") }
                    Button(onClick = {
                        val source = bitmap ?: return@Button
                        if (frame.width <= 0 || frame.height <= 0 || busy) return@Button
                        busy = true
                        val savedZoom = zoom
                        val savedPan = pan
                        val savedFrame = frame
                        scope.launch {
                            try {
                                val result = withContext(Dispatchers.IO) {
                                    val fw = savedFrame.width.toFloat()
                                    val fh = savedFrame.height.toFloat()
                                    val scale = max(fw / source.width, fh / source.height) * savedZoom
                                    val left = (fw - source.width * scale) / 2f + savedPan.x
                                    val top = (fh - source.height * scale) / 2f + savedPan.y
                                    val x = ((-left) / scale).roundToInt().coerceIn(0, source.width - 1)
                                    val y = ((-top) / scale).roundToInt().coerceIn(0, source.height - 1)
                                    val cw = (fw / scale).roundToInt().coerceIn(1, source.width - x)
                                    val ch = (fh / scale).roundToInt().coerceIn(1, source.height - y)
                                    val cut = Bitmap.createBitmap(source, x, y, cw, ch)
                                    val outW = if (aspectRatio >= 1f) 1920 else 1200
                                    val outH = (outW / aspectRatio).roundToInt().coerceAtLeast(1)
                                    val resized = Bitmap.createScaledBitmap(cut, outW, outH, true)
                                    if (resized !== cut) cut.recycle()
                                    val file = File(context.cacheDir, "elory-crop-" + System.nanoTime() + ".webp")
                                    try {
                                        file.outputStream().use { if (!resized.compress(Bitmap.CompressFormat.WEBP, 88, it)) throw IOException("تعذر حفظ الصورة بعد القص") }
                                    } finally { resized.recycle() }
                                    Uri.fromFile(file)
                                }
                                onCropped(result)
                            } catch (e: Exception) {
                                error = e.localizedMessage ?: "تعذر تجهيز الصورة"
                            } finally { busy = false }
                        }
                    }, enabled = src != null && error == null && !busy, modifier = Modifier.weight(1f)) {
                        if (busy) CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp) else Text("اعتماد الصورة")
                    }
                }
            }
        }
    }
}
